from pyniexp.connection import Tcp
from pyniexp import utils
import re#, dicom
import numpy
from scipy.linalg import null_space
from numpy.linalg import det

import pickle

required_fields = [
    'AcquisitionMatrix',
    'NumberOfImagesInMosaic',
    'PixelSpacing',
    'SpacingBetweenSlices',
    'ImagePositionPatient',
    'ImageOrientationPatient',
    'Columns',
    'Rows',
    'SliceNormalVector'
]

class TcpDicom(Tcp):
    
    def __init__(self,port=5677,control_signal=[0,0]):
        super().__init__(port=port,control_signal=control_signal,encoding='latin-1') 
        
        self.header = {}
        self.watch_dir = ''

        # self.open_as_server()

    def receive_initial(self,hdr=None):
        if hdr is None:
            data = self.receive_data(n=2,dtype='uint')
            hdr = self.receive_data(n=data[0],dtype='str').split('\n')
            #with open('hdr_initial.pkl','wb') as f:
            #    pickle.dump(hdr, f)
        
        t = get_header_data(hdr,'ParamLong."NImageLins"') + get_header_data(hdr,'ParamLong."NImageCols"')
        t = [int(i) for i in t if not(i is None)]
        if len(t) == 2: self.header['AcquisitionMatrix'] = t

        t = get_header_data(hdr,'ParamDouble."RoFOV"') + get_header_data(hdr,'ParamDouble."PeFOV"')
        t = [int(i) for i in t if not(i is None)]
        if len(t) == 2: self.header['PixelSpacing'] = [t[i]/self.header['AcquisitionMatrix'][i] for i in range(0,2)]

    def receive_scan(self,hdr=None,img=None):
        if hdr is None or img is None:
            data = self.receive_data(n=2,dtype='uint')
            hdr = self.receive_data(n=data[0],dtype='str').split('\n')
            img = self.receive_data(n=int(data[1]/2),dtype='ushort')
            # with open('hdr_img{:d}.pkl'.format(i),'wb') as f:
            #    pickle.dump([hdr, img], f)
        if not(self.is_header_complete):
            if len(self.watch_dir): 
                pass
            else:
                t = get_header_data(hdr,'DICOM.ImagesInMosaic')[0]
                if not(t is None): self.header['NumberOfImagesInMosaic'] = int(t)
                t = get_header_data(hdr,'DICOM.SpacingBetweenSlices')[0]
                if not(t is None): self.header['SpacingBetweenSlices'] = t
                # TODO: ImagePositionPatient # 3x1
                t = []
                t += get_header_data(hdr,'RowVec.dSag')
                t += get_header_data(hdr,'RowVec.dCor')
                t += get_header_data(hdr,'RowVec.dTra')
                t += get_header_data(hdr,'ColumnVec.dSag')
                t += get_header_data(hdr,'ColumnVec.dCor')
                t += get_header_data(hdr,'ColumnVec.dTra')
                if not(any([i is None for i in t])): self.header['ImageOrientationPatient'] = t
                t = get_header_data(hdr,'DICOM.NoOfCols')[0]
                if not(t is None): self.header['Columns'] = int(t)
                t = get_header_data(hdr,'DICOM.NoOfRows')[0]
                if not(t is None): self.header['Rows'] = int(t)
                t = get_header_data(hdr,'DICOM.SlcNormVector',multiple=True)
                if not(any([i is None for i in t])): self.header['SliceNormalVector'] = t
                t = get_header_data(hdr,'DICOM.MosaicRefAcqTimes',multiple=True)
                if not(any([i is None for i in t])): self.header['SliceTimes'] = t
        if self.is_header_complete:
            self.header = parse_header(self.header)
    
    @property
    def is_header_complete(self):
        return all(utils.ismember(required_fields,list(self.header.keys())))

# ---------------------------------------- UTILS -------------------------------------
def get_header_data(hdr,field,multiple=False):
    ind = utils.list_find(hdr,field)
    if not(len(ind)): return [None]
    if not(multiple): ind = [ind[0]]

    val = list(); field0 = field
    for i in range(0,len(ind)):
        dat = None
        if len(ind) > 1: field = '{}.{:d}'.format(field0,i)
        else: field = field0
        t = re.search(field +' = ([-+]?[0-9]*\.?[0-9]*)',hdr[ind[i]])
        if t is None: t = re.search('<'+ field +'>  { ([-+]?[0-9]*\.?[0-9]*)  }',hdr[ind[i]]) # intro header v1
        if t is None: t = re.search('<'+ field +'>  { <Precision> 16  ([-+]?[0-9]*\.?[0-9]*)  }',hdr[ind[i]]) # intro header v2
        if not(t is None): 
            dat = float(t.groups(1)[0])
        val.append(dat)
    return val

def parse_header(hdr):
#   Based on spm_dicom_convert Id 6190 2014-09-23 16:10:50Z guillaume $
#       by John Ashburner & Jesper Andersson
#       Part of SPM by Wellcome Trust Centre for Neuroimaging

    # Resolution
    hdr['Dimensions'] = hdr['AcquisitionMatrix'] + [hdr['NumberOfImagesInMosaic']]
    hdr['PixelDimensions'] = hdr['PixelSpacing'] + [hdr['SpacingBetweenSlices']]

    # Transformation matrix
    analyze_to_dicom = numpy.matmul(numpy.concatenate((numpy.concatenate((numpy.diag([1, -1, 1]), numpy.array([0,hdr['AcquisitionMatrix'][1]-1,0]).reshape(-1,1)),axis=1),numpy.array([0, 0, 0, 1]).reshape(1,-1)),axis=0),
        numpy.concatenate((numpy.eye(4,3), numpy.array([-1, -1, -1, 1]).reshape(-1,1)),axis=1))
    
    vox = hdr['PixelDimensions']
    pos = numpy.array(hdr['ImagePositionPatient']).reshape(-1,1)
    orient = numpy.array(hdr['ImageOrientationPatient']).reshape(2,3).transpose()
    orient = numpy.concatenate((orient, null_space(orient.transpose())), axis=1)
    if det(orient)<0: orient[:,2] = -orient[:,2]
    dicom_to_patient = numpy.concatenate((numpy.concatenate((numpy.matmul(orient,numpy.diag(vox)),pos),axis=1),numpy.array([0,0,0,1]).reshape(1,-1)),axis=0)
    truepos = numpy.matmul(dicom_to_patient,numpy.concatenate(((numpy.array([hdr['Columns'],hdr['Rows']])-numpy.array(hdr['AcquisitionMatrix']))/2,numpy.array([0,1]))).reshape(-1,1))
    dicom_to_patient = numpy.concatenate((numpy.concatenate((numpy.matmul(orient,numpy.diag(vox)),truepos[0:3]),axis=1),numpy.array([0,0,0,1]).reshape(1,-1)),axis=0)

    patient_to_tal = numpy.diag([-1, -1, 1,1])

    mat = numpy.matmul(patient_to_tal, dicom_to_patient, analyze_to_dicom)

    if det(numpy.concatenate((numpy.array(hdr['ImageOrientationPatient']).reshape(2,3).transpose(), numpy.array(hdr['SliceNormalVector']).reshape(-1,1)), axis=1))<0:
        mat = numpy.matmul(mat,numpy.concatenate((numpy.concatenate((numpy.eye(3),numpy.array([0,0,-(hdr['Dimensions'][2]-1)]).reshape(-1,1)),axis=1),numpy.array([0,0,0,1]).reshape(1,-1)),axis=0))

    hdr['mat'] = mat
    return hdr

hdr_ini = pickle.load(open('D:\Private\OneDrive - Royal Holloway University of London\Project\OpenNFT\DICOMExport\hdr_initial.pkl','rb'))
hdr = pickle.load(open('D:\Private\OneDrive - Royal Holloway University of London\Project\OpenNFT\DICOMExport\hdr_img0.pkl','rb'))[0]
rtd = TcpDicom()
rtd.receive_initial(hdr_ini)
rtd.receive_scan(hdr,1)
hdr = rtd.header
hdr['ImagePositionPatient'] = [-578, -576, -39]
hdr = parse_header(hdr)