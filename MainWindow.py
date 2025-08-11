import glob
import os.path
import time


import cv2
from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeyEvent, QFont
from PyQt5.QtWidgets import (QWidget, QGroupBox, QPushButton, QFileDialog,
                            QLabel, QVBoxLayout, QHBoxLayout,QMessageBox)
import numpy as np
import random
import json
from utils.dataUtils import CsvLog
from utils.annoUtils import parseLabelmeXMl
from utils.gazeUtils import getGazeCenter, getGazeRaw,eyeTrackerInit
from utils.imageUtils import (createPixmapFromArray, imRead, crossHair, superimposeHeatmapToImage,
                              drawBBoxesOnImage, getImageFileSize, pointToHeatmap, pointToImage)


# TODO: 1. space+(0,1,2,3,4) for class label and move to next image     -> finished
#       2. get image position                                           -> finished
#       3. get the Eyetracker in                                        -> finished
#       4. get the photoshop-like opening                               -> finished
#       5. image resize                                                 -> finished
#       6. logging, all the data should be saved in csv.                -> finished
#       7. Add user hint                                                -> finished
#       8. Add bbox support                                             -> finished
#       9. Add folder selector                                          -> Replaced with config.json
#       10.Add Dark Mode                                                -> finished
#       11.add name text Box and where you want to save                 -> finished
#       12.setting in config.json                                       -> finished
#       13.Add 'Last image' button


def getPointInImage(absPoint, imPosition):
    # print("预测点", absPoint[0], absPoint[1])
    x, y = [absPoint[0] - imPosition[0], absPoint[1] - imPosition[1]]
    x = max(min(imPosition[2], x), 0)
    y = max(min(imPosition[3], y), 0)
    return [x, y]


# The data we want to collect
class Data:
    def __init__(self, fileName: str):
        self.fileName = fileName
        self.classLabel = -1
        self.gazeData = []
        self.indexData = []
        self.bboxs = []
        self.userGazePoint = (-1, -1)
class BlurHole():
    def __init__(self, image):
        self.org = image
        self.blurred = cv2.GaussianBlur(self.org, (39, 39), 0)
        self.shape = self.org.shape

    def getHoleBlur(self, center):

        image = self.org.copy()
        cv2.circle(image, center, 3, color=(245, 0, 0), thickness=-1)
        return image

class MainWindow(QWidget):
    def __init__(self, imageDimension: int):
        super().__init__()
        eyeTrackerInit()
        self.config = json.load(open('config.json'))

        imageDir = QFileDialog.getExistingDirectory(None, "请选择图片文件夹路径", "D:\eye_test")
        self.imageList = glob.glob(imageDir + '/*.jpg') + glob.glob(imageDir + '/*.png')
        sum_images = len(self.imageList)
        #self.imageList=self.imageList.sort()
        if self.config["random display order"]:
            random.shuffle(self.imageList)

        # Only one of the mode would work
        self.cheaterMode = self.config["guide mode"]
        self.instaReviewMode = self.config["insta review"]
        # the cheater mode, insta review mode, etc, is some kind of extension. self.displayingExtension
        # is a flag of whether the displaying content is a extension.
        self.displayingExtension = False
        self.imageListIndex = 0
        self.data = Data(fileName=self.imageList[0])
        self.savePath = os.path.dirname(imageDir)
        self.heatmapPath = os.path.join(self.savePath, "heatmaps")
        # 获取self.heatmapPath中的图片名称，并将self.imageList中与self.heatmapPath的图片名称相同的去掉
        saved_filenames = set(os.path.basename(p) for p in glob.glob(self.heatmapPath + '/*.jpg') + glob.glob(self.heatmapPath + '/*.png'))
        self.imageList = [p for p in self.imageList if os.path.basename(p) not in saved_filenames]
        print(f"总共{sum_images}张图片，还剩{len(self.imageList)}张图片")
        self.createControlBox()
        self.allowDrawBbox = False
        self.scale=self.config["scale"]
        # This is for the time recording
        self.stopWatch = time.time()
        if imageDimension == 2:
            self.createImageBox2D()
        elif imageDimension == 3:
            self.createImageBox3D()
        else:
            raise Exception('imageDimension must 2 or 3.')
        mainLayout = QVBoxLayout()
        mainLayout.addWidget(self.imageBox)
        mainLayout.addWidget(self.controlBox)
        self.setLayout(mainLayout)
        self.setWindowTitle("Gaze_Test")
        font = QFont(self.config['font'], 12)
        font.setBold(True)
        self.setFont(font)
        self.refreshTimer = QtCore.QTimer(self)
        self.refreshTimer.timeout.connect(self.refresh)
        self.refreshTimer.start(200)
        self.saveTimer = QtCore.QTimer(self)
        # self.saveTimer.start(2000)
        # self.saveTimer.timeout.connect(self.resave)

    # This part is about eye track log system
    def setLogSystem(self, volunteerName: str, saveTo: str):
        self.logSystem = CsvLog(volunteerName, saveTo)

    # This function controls all the keyboard event
    def keyPressEvent(self, event: QKeyEvent) -> None:
        key = event.key()
        if key == Qt.Key_Escape and self.displayingExtension:
            self.nextImage()
            self.displayingExtension = False

        elif key == Qt.Key_1:
            self.data.gazeData = []
        elif key == Qt.Key_2:
            self.data.classLabel = chr(key)
            self.my_own_save_data()
            self.instaReview()
        elif key == Qt.Key_3:
            self.nextImage() 
        elif key == Qt.Key_L:
            self.drawCrossHair()


    def my_own_save_data(self):
        currentImageFile = self.imageList[self.imageListIndex]
        currentImage = imRead(self.imageList[self.imageListIndex])
        originalWeight, originalHeight = getImageFileSize(currentImageFile)
        # currentImageWithBBoxes = drawBBoxesOnImage(currentImage, labels, scaleFactor=self.imageHeight / originalHeight)
        gazeHeatmap, gaze, onehot = pointToHeatmap(self.data.gazeData, heatmapShape=currentImage.shape)
        self.saveImage(currentImageFile,gazeHeatmap,gaze,onehot,originalWeight, originalHeight)
        # self.just_save_heatmap(currentImageFile,gazeHeatmap,originalWeight, originalHeight)
        # imageWithHeatmap = superimposeHeatmapToImage(heatmap=gazeHeatmap, image=currentImage)
        imageWithPoints = pointToImage(onehot=onehot, image=currentImage)

        self.imageLabel.setPixmap(createPixmapFromArray(imageWithPoints))

    def just_save_heatmap(self, current, heat_img, originalWeight, originalHeight):
        heatmap_name = current.split('\\')[-1]
        save_heatmap=os.path.join(self.savePath,heatmap_name)
        heat_img=cv2.resize(heat_img,(originalWeight, originalHeight))
        cv2.imwrite(save_heatmap, heat_img)
        print(f"图片已保存在{save_heatmap}")


    # This part is about bbox drawing
    def __setAllowDrawBboxTrue(self):
        self.allowDrawBbox = True

    def __setAllowDrawBboxFalse(self):
        self.allowDrawBbox = False

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if self.allowDrawBbox and event.button() == Qt.LeftButton:
            self.__bboxStartX = event.x()
            self.__bboxStartY = event.y()

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        if self.allowDrawBbox and event.button() == Qt.LeftButton:
            thisBbox = (self.__bboxStartX, self.__bboxStartY, event.x(), event.y())
            imageX, imageY = (self.imageLabel.frameGeometry().x() + self.imageBox.frameGeometry().x(),
                              self.imageLabel.frameGeometry().y() + self.imageBox.frameGeometry().y())
            thisBbox = (thisBbox[0] - imageX, thisBbox[1] - imageY, thisBbox[2] - imageX, thisBbox[3] - imageY)
            self.data.bboxs.append(thisBbox)
            self.allowDrawBbox = False
            self.drawBBox(*thisBbox)

    # def getImageGeometry(self):
    #     windowGeometry = self.frameGeometry()
    #     imageGeometry = self.imageLabel.frameGeometry()
    #     boxGeometry = self.imageBox.frameGeometry()
    #     imageAbsGeometry = (windowGeometry.x() + imageGeometry.x() + boxGeometry.x(),
    #                         windowGeometry.y() + imageGeometry.y() + boxGeometry.y(),
    #                         imageGeometry.width(),
    #                         imageGeometry.height())
    #     return imageAbsGeometry#返回图像的位置
    def getImageGeometry(self):
        # 获取 imageLabel 相对于屏幕的位置（左上角）
        topLeft = self.imageLabel.mapToGlobal(QtCore.QPoint(0, 0))
        width = self.imageLabel.width()
        height = self.imageLabel.height()

        imageAbsGeometry = (topLeft.x(), topLeft.y(), width, height)
        return imageAbsGeometry


    # 添加中文的确认退出提示框1
    def closeEvent(self, event):
        # 创建一个消息盒子（提示框）
        quitMsgBox = QMessageBox()
        # 设置提示框的标题
        quitMsgBox.setWindowTitle('确认提示')
        # 设置提示框的内容
        quitMsgBox.setText('你确认退出吗？')
        # 设置按钮标准，一个yes一个no
        quitMsgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        # 获取两个按钮并且修改显示文本
        buttonY = quitMsgBox.button(QMessageBox.Yes)
        buttonY.setText('确定')
        buttonN = quitMsgBox.button(QMessageBox.No)
        buttonN.setText('取消')
        quitMsgBox.exec_()
        # 判断返回值，如果点击的是Yes按钮，我们就关闭组件和应用，否则就忽略关闭事件
        if quitMsgBox.clickedButton() == buttonY:
            event.accept()
        else:
            event.ignore()

    def nextImage(self):
        self.imageListIndex += 1
        if self.imageListIndex==len(self.imageList):
            QMessageBox.warning(None,'警告','已经是最后一张图片',QMessageBox.Yes,QMessageBox.Yes)
            return
        currentImage = imRead(self.imageList[self.imageListIndex],resize=self.scale)
        self.refreshTimer.start(100)
        self.imageLabel.setPixmap(createPixmapFromArray(currentImage))
        # reset the eye tracker and stop watch
        getGazeRaw()
        self.stopWatch=time.time()
        self.blurHole = BlurHole(currentImage)
        self.data = Data(self.imageList[self.imageListIndex])
        # print(self.imageListIndex)

    def resave(self):
        gaze=[getPointInImage(x, self.getImageGeometry()) for x in getGazeRaw()]
        gazeData=[]
        self.saveRoot='./'
        for g in gaze:
            gazeData.append(g)
        save_dir=os.path.join(self.saveRoot,'onehot')
        currentImageFile = self.imageList[self.imageListIndex]
        labels = parseLabelmeXMl(currentImageFile)
        currentImage = imRead(self.imageList[self.imageListIndex], resize=self.scale)
        _, originalHeight = getImageFileSize(currentImageFile)
        gazeHeatmap, onehot = pointToHeatmap(gazeData, heatmapShape=currentImage.shape)

        np.save(os.path.join(save_dir,'onehot.npy'),onehot)
        cv2.imwrite(os.path.join(self.saveRoot,'heatmap','heatmap.png'),gazeHeatmap)

    def saveImage(self,current,heat_img,g,onehot,originalWeight, originalHeight):
        image_name = current.split('\\')[-1]
        heatmap_name=image_name.split('.')[0]+'_heatmap.png'
        gaze_name=image_name.split('.')[0]+'_gaze.npy'
        onehot_name=image_name.split('.')[0]+'_onehot.npy'
        points_name=image_name.split('.')[0]+'_points.npz'
        save_heatmap=os.path.join(self.savePath,'heatmaps',heatmap_name)
        save_gaze=os.path.join(self.savePath,'gaze',gaze_name)
        save_onehot=os.path.join(self.savePath,'onehot',onehot_name)
        save_points=os.path.join(self.savePath,'points',points_name)
        if not os.path.exists(os.path.join(self.savePath,'heatmap')):
            os.makedirs(os.path.join(self.savePath,'heatmaps'))
            os.makedirs(os.path.join(self.savePath,'gaze'))
            os.makedirs(os.path.join(self.savePath,'onehot'))
            os.makedirs(os.path.join(self.savePath,'points'))
        points=np.array(self.data.gazeData)
        index=np.array(self.data.indexData)
        np.savez(save_points, points=points,index=index)
        heat_img=cv2.resize(heat_img,(originalWeight, originalHeight))
        g=cv2.resize(g,(originalWeight, originalHeight))
        onehot=cv2.resize(onehot,(originalWeight, originalHeight))
        cv2.imwrite(save_heatmap, heat_img)
        np.save(save_gaze, g)
        np.save(save_onehot, onehot)

    def instaReview(self):
        if int(self.data.classLabel)==2:
            self.refreshTimer.stop()
            currentImageFile = self.imageList[self.imageListIndex]
            labels = parseLabelmeXMl(currentImageFile)
            currentImage = imRead(self.imageList[self.imageListIndex],resize=self.scale)
            originalWeight, originalHeight = getImageFileSize(currentImageFile)
            #currentImageWithBBoxes = drawBBoxesOnImage(currentImage, labels, scaleFactor=self.imageHeight / originalHeight)
            gazeHeatmap,gaze,onehot = pointToHeatmap(self.data.gazeData, heatmapShape=currentImage.shape)
            # self.saveImage(currentImageFile,gazeHeatmap,gaze,onehot,originalWeight, originalHeight)

            #imageWithHeatmap = superimposeHeatmapToImage(heatmap=gazeHeatmap, image=currentImage)
            imageWithPoints = pointToImage(onehot=onehot, image=currentImage)

            self.imageLabel.setPixmap(createPixmapFromArray(imageWithPoints))
        else:
            self.data.gazeData.clear()
            self.refreshTimer.start()

    def drawAttentionMap(self):
        pass

    # This function create the UI of Image Display
    def createImageBox2D(self):
        self.imageBox = QGroupBox("")
        self.imageLabel = QLabel()
        image = imRead(self.imageList[0], resize=self.scale)
        self.imageLabel.setPixmap(createPixmapFromArray(image))
        layout = QVBoxLayout()
        layout.addWidget(self.imageLabel)
        self.imageBox.setLayout(layout)
        self.blurHole = BlurHole(image)

    # This function create the UI of control panel
    def createControlBox(self):
        self.controlBox = QGroupBox("")
        #startButton = QPushButton("Start")
        nextButton = QPushButton("Next Image")

        #lastButton = QPushButton("Last Image")
        #bboxButton = QPushButton("Add Bounding Boxes")
        closeButton = QPushButton("Exit")

        #startButton.clicked.connect(self.start)
        nextButton.clicked.connect(self.nextImage)
        closeButton.clicked.connect(self.close)
        #bboxButton.clicked.connect(self.__setAllowDrawBboxTrue)
        layout = QHBoxLayout()
        #layout.addWidget(startButton)
        layout.addWidget(nextButton)
        #layout.addWidget(lastButton)
        #layout.addWidget(bboxButton)
        layout.addWidget(closeButton)
        self.controlBox.setLayout(layout)

    def refresh(self):
        gaze = getGazeCenter(lastN = 100, width = self.config["width"], height = self.config["height"])

        #points = [getPointInImage(x, self.getImageGeometry()) for x in points]
        if not gaze:
            return
        # for p in points:
        #     self.data.gazeData.append(p)
        gaze = getPointInImage(gaze, self.getImageGeometry())
        self.data.gazeData.append(gaze)
        self.data.indexData.append(0)
        if len(self.data.gazeData) > 1:
            pre_point = np.array(self.data.gazeData[-2])
            point = np.array(self.data.gazeData[-1])
            dist = (((point - pre_point) ** 2).sum() ** 0.5)
            i = 1 if dist > 15 else 0
            self.data.indexData[-1] = i
        image = self.blurHole.getHoleBlur(center=gaze)
        self.imageLabel.setPixmap(createPixmapFromArray(image))
