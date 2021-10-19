from numpy.core.arrayprint import format_float_positional
import torch
import cv2
import numpy as np
from tool.scoring import Scoring
import data.sampleColor as myColor
from model.VGG16 import myModel
import matplotlib.pyplot as plt
from model.VGG16_rf20 import VGG16_rf20
from model.ResNet34 import ResNet34
from model.ResNet34_lin import ResNet34_lin
import torch.nn.functional as nnf
import glob
import os
import torch.nn.functional as F
import torch

from back_logic.segmentation import EDseg
from back_logic.evaluate import EDeval
import time

class Inference():
    def __init__(self, args):
        self.cfg = args
        # self.device = torch.device('cuda:0')
        self.device = torch.device('cpu')
        self.model_path = self.cfg.model_path
        self.image_path = self.cfg.image_path
        self.image_save_path = self.cfg.save_path
        self.gt_path = self.cfg.save_path
        self.max_arg = 0
        self.model = None
        self.max_arg = 0
        # self.model.maxArg


    def inference(self):
        #----------------------- Get Model ---------------------------------------------

        self.max_arg = self.model.maxArg
        #----------------------- Get Image ---------------------------------------------

        img = cv2.imread(self.image_path)
        img = cv2.resize(img, (self.model.output_size[1], self.model.output_size[0]))
        input_tensor = torch.from_numpy(np.expand_dims(img, axis=0)).permute(0,3,1,2).float()

        #----------------------- Inference ---------------------------------------------

        output_tensor = self.model(input_tensor)
        output_image = output_tensor[0].permute(1,2,0).detach().numpy()
        #----------------------- Show Image ---------------------------------------------
        if self.cfg.show:
            self.show_image(img)
        #----------------------- Save Image ---------------------------------------------
        else:
            self.save_image(output_image)



    def save_image(self, image, fileName):
        # --------------------------Save segmented map
        fir_dir = os.path.join(self.image_save_path,str(fileName)+".jpg")
        print(fir_dir)

        # --------------------------Save SegImg ____ 
        image = cv2.resize(image, (300,180))
        cv2.imwrite(fir_dir, image)
        return

    def show_image(self, img):

        input_tensor = torch.from_numpy(np.expand_dims(img, axis=0)).permute(0,3,1,2).float()
        output_tensor = self.model(input_tensor)
        m = torch.nn.Softmax(dim=0)


        cls_soft = torch.max(m(output_tensor[0][:]).detach(), 0)
        score = Scoring()
        score.prob2lane(cls_soft, 40, 350, 5 )

        cls_img = cls_soft.indices.detach().numpy().astype(np.uint8)
        cls_img = cv2.cvtColor(cls_img, cv2.COLOR_GRAY2BGR)
        for idx, lanes in enumerate(score.lanes):
            if len(lanes) <=2:
                continue
            for node in lanes:
                cls_img = cv2.circle(cls_img, (node[1],node[0]), 3, myColor.color_list[idx])
        cv2.imshow("ori",img)
        img =cv2.resize(img, (1280, 720))
        cls_img = cv2.resize(cls_img, (1280, 720), interpolation=cv2.INTER_NEAREST)


        #----------- Show Image ---------------
        output_image = output_tensor[0].detach().numpy()
        for idx, out_img in enumerate(output_image):
            cv2.imshow("output {}".format(idx),(255-out_img*80))
            idx +=1
        cv2.imshow("SOFT MAX",cls_img*30)
        cv2.imshow("ori_re",cv2.resize(img, (1280, 720)))

        # temp_tensor = torch.from_numpy(img).permute(2, 0, 1).int()
        # temp_tensor = torch.from_numpy(img).int()
        # temp_tensor.view()
        # input_tensor.view("ori_TENSOR",cv2.resize(img, (1280, 720)))
        # plt.imshow(temp_tensor)
        # plt.show()
        if self.cfg.showAll:
            cv2.waitKey(1)
        else:
            cv2.waitKey()
        return

    def inference_all(self):
        

        path=self.cfg.image_path
        folder_list= glob.glob(os.path.join(path,"*"))

        for folder_path in folder_list:       
            sub_folder_list = glob.glob(os.path.join(folder_path, "*"))
            for folder in sub_folder_list:
                #----------------------- Get Image ---------------------------------------------
                filepath = os.path.join(folder,"20.jpg")
                img = cv2.imread(filepath)
                img = cv2.resize(img, (self.model.output_size[1], self.model.output_size[0]))
                self.show_image(img)
                
            print("Inference Finished!")
        return 


    def inference_dir(self):
        print("SEDFSDFSDF")
        lanelist = []
        pathlist = []
        self.model = self.model.to(self.device)
        path=self.cfg.image_path
        folder_list= glob.glob(os.path.join(path,"*"))
        print(folder_list)
        print(folder_list)
        file_num=0
        for folder_path in folder_list:       
            sub_folder_list = glob.glob(os.path.join(folder_path, "*"))
            for folder in sub_folder_list:
                file_num+=1
        print(file_num)
        print(folder_list)
        for folder_path in folder_list: 
            print(folder_path)
            
            sub_folder_list = glob.glob(os.path.join(folder_path, "*"))
        cur_file=0
        for folder_path in folder_list:       
            sub_folder_list = glob.glob(os.path.join(folder_path, "*"))
            for folder in sub_folder_list:
                filepath = os.path.join(folder,"20.jpg")

                path_list = filepath.split('\\')
                re_path = os.path.join(*path_list[-4:])
                pathlist.append(re_path)
                #----------------------- Get Image ---------------------------------------------
                img = cv2.imread(filepath)
                img_tensor = torch.from_numpy(img).to(self.device)

                
                img = cv2.resize(img, (self.model.output_size[1], self.model.output_size[0]))

                img_tensor = nnf.interpolate( torch.unsqueeze(img_tensor, dim=0).permute(0,3,1,2), size=(self.model.output_size[0], self.model.output_size[1])).float()
                score = self.getScoreInstance3(img_tensor, re_path)

                lanelist.append(score.lane_list)
                if len(lanelist)%200==0:
                    print("Idx {}".format(len(lanelist)))
            print("Inference Finished!")
        return lanelist, pathlist

    def inference_instance(self, input):
        output_tensor = self.model(input)
        output = output_tensor[0].permute(1,2,0).detach().numpy()
        return output
    

    def getScoreInstance3(self, input_tensor, path):
        path_list = path.split('/')
        start = time.time()
        print(input_tensor.shape)
        output_tensor = self.model(input_tensor).to(self.device)
        inference_time = time.time()

        print("Inference time={}".format(inference_time - start))
        
        m = torch.nn.Softmax(dim=0)
        cls_soft = torch.max(m(output_tensor[0][:]).detach(), 0)   
    
        softmax_time = time.time()
        print("softmax_time time={}".format(softmax_time - inference_time))
        
        score = Scoring()
        score.prob2lane(cls_soft, 40, 350, 5 )
        
        seg2lane_time = time.time()
        print("seg2lane_time time={}".format(seg2lane_time - softmax_time))
        
        score.getLanebyH_sample(160, 710, 10)
        
        getH_time = time.time()
        print("getH_time time={}".format(getH_time - seg2lane_time)) 
        return score
        cls_img = cls_soft.indices.detach().numpy().astype(np.uint8)
        cls_img = cv2.cvtColor(cls_img, cv2.COLOR_GRAY2BGR)


        cls_img = cv2.resize(cls_img, (1280, 720), interpolation=cv2.INTER_NEAREST)

        print("--------------")
        for idx, lanes in enumerate(score.lanes):
            print("LANE {}".format(idx))
            if len(lanes) <=2:
                continue
            for node in lanes:
                cls_img = cv2.circle(cls_img, (node[1],node[0]), 50, myColor.color_list[idx])
        gt_img = cv2.imread(gt_path)
        gt_img = cv2.cvtColor(gt_img, cv2.COLOR_BGR2GRAY)
        # img =cv2.resize(img, (1280, 720))

        # if len(score.lanes)==4 or len(score.lanes)==5:
        #     return score
        #----------- Show Image ---------------
        output_image = output_tensor[0].detach().numpy()
        for idx, out_img in enumerate(output_image):
            cv2.imshow("output {}".format(idx),(255-out_img*80))
            idx +=1

        # cv2.imshow("ori",img)
        cv2.imshow("gt",gt_img*30)
        cv2.imshow("SOFT MAX",cls_img*30)
        cv2.waitKey(100)
        return score