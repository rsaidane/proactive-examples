
print("BEGIN FCN")

import json
from ast import literal_eval as make_tuple

IMG_SIZE = variables.get("IMG_SIZE")
NUM_CLASSES = int(str(variables.get("NUM_CLASSES")))
 
IMG_SIZE = make_tuple(IMG_SIZE)

if NUM_CLASSES == 2:
    NUM_CLASSES = NUM_CLASSES - 1       
else:
    NUM_CLASSES = NUM_CLASSES + 2   

# Define the NET model
NET_MODEL = """

class FCN16(nn.Module):

    def __init__(self, num_classes):
        super().__init__()

        feats = list(models.vgg16(pretrained=True).features.children())
        self.feats = nn.Sequential(*feats[0:16])
        self.feat4 = nn.Sequential(*feats[17:23])
        self.feat5 = nn.Sequential(*feats[24:30])
        self.fconn = nn.Sequential(
            nn.Conv2d(512, 4096, 7),
            nn.ReLU(inplace=True),
            nn.Dropout(),
            nn.Conv2d(4096, 4096, 1),
            nn.ReLU(inplace=True),
            nn.Dropout(),
        )
        self.score_fconn = nn.Conv2d(4096, num_classes, 1)
        self.score_feat4 = nn.Conv2d(512, num_classes, 1)

    def forward(self, x):
        feats = self.feats(x)
        feat4 = self.feat4(feats)
        feat5 = self.feat5(feat4)
        fconn = self.fconn(feat5)

        score_feat4 = self.score_feat4(feat4)
        score_fconn = self.score_fconn(fconn)

        score = F.upsample_bilinear(score_fconn, score_feat4.size()[2:])
        score += score_feat4

        return F.upsample_bilinear(score, x.size()[2:])
        
        
METHOD_NAME = 'fcn16'        
Net = FCN16
assert Net is not None, f'model {MODEL_NAME} not available'
model = Net(NUM_CLASSES)
        
"""
print(NET_MODEL)

# Data augmentation and normalization for training
# Just normalization for validation and test
NET_TRANSFORM = """
import numpy as np
def colormap(n):
    cmap=np.zeros([n, 3]).astype(np.uint8)

    for i in np.arange(n):
        r, g, b = np.zeros(3)

        for j in np.arange(8):
            r = r + (1<<(7-j))*((i&(1<<(3*j))) >> (3*j))
            g = g + (1<<(7-j))*((i&(1<<(3*j+1))) >> (3*j+1))
            b = b + (1<<(7-j))*((i&(1<<(3*j+2))) >> (3*j+2))

        cmap[i,:] = np.array([r, g, b])

    return cmap

class Relabel:

    def __init__(self, olabel, nlabel):
        self.olabel = olabel
        self.nlabel = nlabel

    def __call__(self, tensor):
        assert isinstance(tensor, torch.LongTensor), 'tensor needs to be LongTensor'
        tensor[tensor == self.olabel] = self.nlabel
        return tensor


class ToLabel:

    def __call__(self, image):
        return torch.from_numpy(np.array(image)).long().unsqueeze(0)


class Colorize:

    def __init__(self, n=22):
        self.cmap = colormap(256)
        self.cmap[n] = self.cmap[-1]
        self.cmap = torch.from_numpy(self.cmap[:n])

    def __call__(self, gray_image):
        size = gray_image.size()
        color_image = torch.ByteTensor(3, size[1], size[2]).fill_(0)

        for label in range(1, len(self.cmap)):
            mask = gray_image[0] == label

            color_image[0][mask] = self.cmap[label][0]
            color_image[1][mask] = self.cmap[label][1]
            color_image[2][mask] = self.cmap[label][2]

        return color_image
        
if NUM_CLASSES == 1:
    input_transform = Compose([Resize(IMG_SIZE),ToTensor()])
    target_transform = Compose([Resize(IMG_SIZE),ToTensor()])
else:
    color_transform = Colorize()
    image_transform = ToPILImage()
    input_transform = Compose([
            Resize(IMG_SIZE),   
            ToTensor(),
            Normalize([.485, .456, .406], [.229, .224, .225]),
    ])
    target_transform = Compose([
            Resize(IMG_SIZE),     
            ToLabel(),
            Relabel(255, 21),
    ])
"""
print(NET_TRANSFORM)

#CRITERION FUNCTION
NET_CRITERION = """
class CrossEntropyLoss2d(nn.Module):

    def __init__(self, weight=None):
        super().__init__()

        self.loss = nn.NLLLoss2d(weight)

    def forward(self, outputs, targets):
        return self.loss(F.log_softmax(outputs), targets)

class BinaryCrossEntropyLoss2d(nn.Module):

    def __init__(self, weight=None):
        super().__init__()
        
        #self.loss = nn.BCELoss(weight)
        self.loss = nn.BCEWithLogitsLoss(weight)

    def forward(self, outputs, targets):
        #return self.loss(nn.Sigmoid(outputs), targets)
        return self.loss(outputs, targets)
        
"""
print(NET_CRITERION)


if 'variables' in locals():
  variables.put("NET_MODEL", NET_MODEL)
  variables.put("NET_TRANSFORM", NET_TRANSFORM)
  variables.put("NET_CRITERION", NET_CRITERION)
  variables.put("IMG_SIZE", IMG_SIZE)
  variables.put("NUM_CLASSES", NUM_CLASSES)

print("END FCN")