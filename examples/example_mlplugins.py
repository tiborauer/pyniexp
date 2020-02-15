# OpenNFT is required

from opennft import mlproc
from pyniexp.mlplugins import imageProcess
from time import sleep

imgDim = (5,5,3)

class myImageProcess(imageProcess):
    def process(self,image):
        print(image[:,:,0])

if __name__ == '__main__':
    mlp = mlproc.MatlabSharedEngineHelper(startup_options='-desktop', shared_name='test')
    mlp.connect(start=True, name_prefix='test')
    mlp.engine.assignin('base','sig',0,nargout=0)

    t = myImageProcess(imgDim)

    it = 0
    while it < 5:
        cit = mlp.engine.evalin('base','sig')
        if cit > it:
            it = cit
            t.load_image(mlp.engine.workspace['img']._data.tolist())
            sleep(2)

    t = None
    mlp.destroy_engine()