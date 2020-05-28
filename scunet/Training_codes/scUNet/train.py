#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Nov 14 18:56:35 2019

@author: lhjin
"""
from xlwt import *
import numpy as np
import os
import math
import torch
from torch.utils.data import  DataLoader
from skimage import io, transform
from mat_file import mat_file
from torchsummary import summary

#import sys
#path = '/home/star/0_code_lhj/DL-SIM-github/Training_codes/scUNet/'
#sys.path.append(path)

from unet_model import UNet
import sys

model = UNet(n_channels=5, n_classes=1)
print(summary(model, (5, 128, 128)))
sys.exit()


class ToTensor(object):
    """Convert ndarrays in sample to Tensors."""

    def __call__(self, sample):
        data_in, data_out = sample['image_in'], sample['groundtruth']

        # swap color axis because
        # numpy image: H x W x C
        # torch image: C X H X W
        #image = image.transpose((2, 0, 1))
        #landmarks = landmarks.transpose((2, 0, 1))
        
        #return {'image': image, 'landmarks': torch.from_numpy(landmarks)}
        return {'image_in': torch.from_numpy(data_in),
               'groundtruth': torch.from_numpy(data_out)}

class ReconsDataset(torch.utils.data.Dataset):
     def __init__(self, train_in_path,train_gt_path, transform, img_type,in_size):
        self.train_in_path = train_in_path
        self.train_gt_path = train_gt_path
        self.transform = transform
        self.img_type = img_type
        self.in_size = in_size
        self.dirs_gt = os.listdir(self.train_gt_path)
     def __len__(self):
        dirs = os.listdir(self.train_gt_path)   # open the files
        return len(dirs)            # because one of the file is for groundtruth

     def __getitem__(self, idx):
         image_name = os.path.join(self.train_gt_path, self.dirs_gt[idx])
         data_gt = io.imread(image_name)
         max_out = 15383.0
         data_gt = data_gt/max_out
         
         filepath = os.path.join(self.train_in_path, self.dirs_gt[idx][:-4])
         #filepath = os.listdir(filepath)
         #train_in_size = len(filepath)
         train_in_size = 15
         
         data_in = np.zeros((self.in_size, self.in_size, train_in_size))
         filepath = os.path.join(self.train_in_path, self.dirs_gt[idx][:-4])
         for i in range(train_in_size):
             if i <= 9:
                 image_name = os.path.join(filepath, "LE_0"+str(i)+"." + self.img_type)
             else:
                image_name = os.path.join(filepath, "LE_"+str(i)+"." + self.img_type)
             image = io.imread(image_name)
             data_in[:,:,i] = image
         max_in = 196.0
         data_in = data_in/max_in
         sample = {'image_in': data_in, 'groundtruth': data_gt}
         
         if self.transform:
             sample = self.transform(sample)
         return sample

def get_learning_rate(epoch):
    limits = [3, 8, 12]
    lrs = [1, 0.1, 0.05, 0.005]
    assert len(lrs) == len(limits) + 1
    for lim, lr in zip(limits, lrs):
        if epoch < lim:
            return lr * learning_rate
        return lrs[-1] * learning_rate




if __name__ == "__main__":
    cuda = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    have_cuda = True if torch.cuda.is_available() else False
    learning_rate = 0.001
    n_channels = 5
    # momentum = 0.99
    # weight_decay = 0.0001
    batch_size = 1
    mf = mat_file()
    X_train, X_test, y_train, y_test = mf.get_images()
    X_train = np.rollaxis(X_train, 3, 1)
    y_train = np.rollaxis(y_train, 3, 1)
    X_test = np.rollaxis(X_test, 3, 1)
    y_test = np.rollaxis(y_test, 3, 1) 

    #print(X_train[0])
    image = torch.from_numpy(X_train).float()
    gt =  torch.from_numpy(y_train).float()
    #print(image.shape)
    train_dataloader = torch.utils.data.DataLoader(X_train, batch_size=batch_size, shuffle=True, pin_memory=False) # better than for loop
    

    model = UNet(n_channels=n_channels, n_classes=1)
    print("{} paramerters in total".format(sum(x.numel() for x in model.parameters())))
    if have_cuda:
        model.cuda(cuda)
    optimizer = torch.optim.Adam(model.parameters(),lr=learning_rate,  betas=(0.9, 0.999))

#    loss_all = np.zeros((2000, 4))
    for epoch in range(2000):
        

        lr = get_learning_rate(epoch)
        for p in optimizer.param_groups:
            p['lr'] = lr
            print("learning rate = {}".format(p['lr']))

        model.train()
        


        gt = gt.float()
        if have_cuda:
            gt = gt.cuda(cuda)
        
        pred = model(image)

        loss = (pred-gt).abs().mean() + 5 * ((pred-gt)**2).mean()
        
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        print ("[Epoch %d] [Batch %d/%d] [loss: %f]" % (epoch, batch_idx, len(train_dataloader), loss.item()))

        torch.save(model.state_dict(), "/home/star/0_code_lhj/DL-SIM-github/Training_codes/scUNet/sUNet_microtubule_"+str(epoch+1)+".pkl")
