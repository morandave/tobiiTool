# 程序运行环境准备
## 眼动仪
第一次将tobii eyetracker 5插到电脑上后会自动下载驱动。然后在网上下载tobii Experience这个软件可进行进行校准。
tobii experience下载链接：https://apps.microsoft.com/detail/9nk75kf67s2n?hl=zh-cn&gl=CN
## Python环境配置
### 安装Anaconda
网上教程：https://blog.csdn.net/wq_ocean_/article/details/103889237
### python package下载
眼动仪的驱动是32位的，所以需要使用32位的python。在Anaconda Prompt中输入：
```bash
set CONDA_SUBDIR=win-32 
conda create -n miceye python=3.7
conda activate miceye
pip install opencv-python numpy pillow qdarkstyle -i https://pypi.tuna.tsinghua.edu.cn/simple
```
还需要下载PyQt5这个包，但这个包需要计算机有14.0以上的版本的C++，需要下载Visual Studio，如果电脑上已经有了就不用下载了。下载方法见链接中方法二：https://blog.csdn.net/JuliaYyyy/article/details/135341170
下好后，在Anaconda Prompt中输入：
```bash
pip install PyQt5 -i https://pypi.tuna.tsinghua.edu.cn/simple
```

## 程序运行
### 参数设置
主要参数：config.json中的`save path`、`width`、`height`,设置为热力图的保存路径和屏幕分辨率。
打开Anaconda Prompt，输入：
```bash
conda activate miceye
cd 程序所在目录
python miceye.py
```
会跳出文件管理器，选择需要观察的图片的文件夹