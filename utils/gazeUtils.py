import TobiiEyeTracker


def getGazeCenter(lastN: int = 100, width: int = 1920, height: int = 1080) -> tuple:#期待输入int类型，输出tuple类型

    buffers = TobiiEyeTracker.getBuffer()
    if len(buffers) == 0:
        return None
    availableSize = min(lastN, len(buffers))
    x = 0.0
    y = 0.0
    for point in buffers[-availableSize:]:
        x += point[0]
        y += point[1]
    points=[[int(p[0] * width), int(p[1] * height)] for p in buffers]
    return int(x / availableSize * width), int(y / availableSize * height)


def getGazeRaw():
    return [[int(p[0] * 1920), int(p[1] * 1080)] for p in TobiiEyeTracker.getBuffer()]


def refresh():
    TobiiEyeTracker.getBuffer()


def eyeTrackerInit():
    try:
        TobiiEyeTracker.init()
    except:
        pass
