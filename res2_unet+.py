#!usr/bin/python
# -*- coding: utf-8 -*-

"""
this file is modified from https://github.com/lessw2020/res2net-plus
"""

import torch
import torch.nn as nn
from torchvision.models.resnet import conv1x1, conv3x3
from torchvision.models.utils import load_state_dict_from_url

#from fastai.torch_core import *
import torch.nn as nn
import torch,math,sys
import torch.utils.model_zoo as model_zoo
from functools import partial

import torch.nn.functional as F
#from ...torch_core import Module
#from fastai.torch_core import Module




class Mish(nn.Module):
    def __init__(self):
        super().__init__()

    def forward(self, x):  
        #save 1 second per epoch with no x= x*() and then return x...just inline it.
        return x *( torch.tanh(F.softplus(x))) 
        #return x * tanh(softplus(x)) = 
        #return x * tanh(ln(1 + e^{x}))
        
act_fn = Mish()

def conv(ni, nf, ks=3, stride=1, bias=False):
    return nn.Conv2d(ni, nf, kernel_size=ks, stride=stride, padding=ks//2, bias=bias)


RESNET_LAYERS = {18: [2, 2, 2, 2], 
                 34: [3, 4, 6, 3], 
                 50: [3, 4, 6, 3],
                 101: [3, 4, 23, 3], 
                 152: [3, 8, 36, 3]}

RES2NEXT_PARAMS = {50: dict(groups=8, width_per_group=4),
                   101: dict(groups=8, width_per_group=8)}

URLS = {
    'res2net50_48w_2s': 'https://u09y8q.dm.files.1drv.com/y4mBXCZMGai94Kqq8v9rTHwQyx7u_w8uX4Ex1HzvKmWWskhKXECh9zhJQLDsJRaA2YPhDbV_xMOKEeltkKS6EArkhwTTY3PyQQOIrBm8gJbN96o8LS2XWu6HsG0iyt06yg7gY7Gy8oOlqH9EMYYJyDdNxh1ICcn2wOjwU6XTXgyeXG1IPMUNnyNiVYDTJwcqLuTfLNnVKojzq3PYlklfOWSZQ/res2net50_48w_2s-afed724a.pth',
    'res2net50_26w_4s': 'https://inui8w.dm.files.1drv.com/y4mhLzHlrNppQEjHEa_IJMBEOqKHKh-DeTQ4Xth_PnI-wGyGMKKyPu_C6RNHDr8Ti1Nw17hYpx-ewU-ugXD6FEqIiRE0qa1NWJrG0C3puGFoIlFAkxo46HujAKMWbWEglhTFn-J30AZZd7vqW4ASqynADCzeo1QfVWwcrIrADD3LYluji-tSIa2iFYkpo-j8rLQ4dZ_z887f3fmT9idCkqeng/res2net50_26w_4s-06e79181.pth',
    'res2net50_14w_8s': 'https://u0po2g.dm.files.1drv.com/y4mWya8g9auU6EgyQGBRsFZ2er5xW6Azd7hLcKUQU-zH3rwtGOhop7h0uewFTD5N1dfeW_WZpQUsLjP-33myzi69_2JhRzppuvyX7223WoyaIG11KCXV5zxoBnlCRbFfh3u7AThTxFA_BQhVPFMaYQt93C-06JKCKA909rLtTH_FxVpo-ZMfcAh819vC7yfQeJ69Z94ZZQhllH2nCA9LntE5A/res2net50_14w_8s-6527dddc.pth',
    'res2net50_26w_6s': 'https://u08ptw.dm.files.1drv.com/y4m4VJ4BKIYWn81yLxG7E2pqQ5gyK9M9uqZZsOoKyNfrkaRJf7zzw3LvbHxhWY_DSlHrDOfgAbcvSDM6H0H8iaidlhWuDveMScUHWgam45-16RpiWs1hENXpUuRy206Jkm224mNnYuR_iK2QZ7K95DDEoHp0DQ5fHE-I-PTNpBV4184KJq0e2IpsELaihDXuOvDV-NPlxwZSI6_5SWsYxpGuw/res2net50_26w_6s-19041792.pth',
    'res2net50_26w_8s': 'https://u0qzzq.dm.files.1drv.com/y4mzlxQhPPLhF0QPfws3kTXboNr9Bn3qEtvoixIinZ6Nr1WjRvjFNnrwj6ABhHsegDO5YGvDF8gaT9kSXGdyt9xfVQv7kB8qMJKYXJefbX9jcBmkW2l1-1xO8dco0RcJzQ0PEPl4tDfJk4JbBC1GiSO4NCSrTGXo1V35uyazHYmQQPIG0csDYqScqFjZW2jqmCwzsny-eoRo_WIbQlGh_IAZA/res2net50_26w_8s-2c7c9f12.pth',
    'res2net101_26w_4s': 'https://u08ica.dm.files.1drv.com/y4mDxCx2nG_ydpaHrQB-xqACLuLtK9hUHFZMt_o4X-SHK1osIiePHq8ClztZNDg2WWKy6wsiotHGgHXN_Cy2M89yLY5-kankE4xXPl-SSEguLAzvpEiJmn5t9jfYVdb_brVgZm5K_rB6-rvUkUqwKwkjCb-GxDBbB2IvAdXIh2n1NfYRgYy2ZOK26gGjPj_7HPD5vY1BfiHrSiLgkgi9cEdpw/res2net101_26w_4s-02a759a1.pth',
    'res2next50_4w_4s_8c': 'https://u0phkw.dm.files.1drv.com/y4mIV0ZmKqI2xBPNrddmnuTTO35aGKgeWiOaVpASZz86z0469ahTme5oaM18wHrMo_c0OXBAahXgQeMz2hEQ2M-Z7znrhN6aAvQfS-FcZ23YO7zE7w0aN9cqrYn1s1-4YbU4ijvUinTVqx4ESYpAuHdb_rfx-OMGE1Qy-_l_5UcVAwQTpM74DTYe6RX0E9uz8qaep0AULZdPRDxKKk7U7ukGA/res2next50_4s-6ef7e7bf.pth'
}


class Res2Block(nn.Module):
    expansion = 4

    def __init__(self, inplanes, planes, stride=1, downsample=None, groups=1,
                 base_width=4, dilation=1, scale=4, first_block=False, norm_layer=None):
        """Implements a residual block
        Args:
            inplanes (int): input channel dimensionality
            planes (int): output channel dimensionality
            stride (int): stride used for conv3x3
            downsample (torch.nn.Module): module used for downsampling
            groups: num of convolution groups
            base_width: base width
            dilation (int): dilation rate of conv3x3            
            scale (int): scaling ratio for cascade convs
            first_block (bool): whether the block is the first to be placed in the conv layer
            norm_layer (torch.nn.Module): norm layer to be used in blocks
        """
        super(Res2Block, self).__init__()
        if norm_layer is None:
            norm_layer = nn.BatchNorm2d

        width = int(planes * (base_width / 64.)) * groups

        self.conv1 = conv1x1(inplanes, width * scale)
        self.bn1 = norm_layer(width * scale)

        # If scale == 1, single conv else identity & (scale - 1) convs
        nb_branches = max(scale, 2) - 1
        if first_block:
            self.pool = nn.AvgPool2d(kernel_size=3, stride=stride, padding=1)
        self.convs = nn.ModuleList([conv3x3(width, width, stride, groups, dilation)
                                    for _ in range(nb_branches)])
        self.bns = nn.ModuleList([norm_layer(width) for _ in range(nb_branches)])
        self.first_block = first_block
        self.scale = scale

        self.conv3 = conv1x1(width * scale, planes * self.expansion)
        
        self.relu = Mish() #nn.ReLU(inplace=False)
        self.bn3 = norm_layer(planes * self.expansion)  #bn reverse

        self.downsample = downsample

    def forward(self, x):

        residual = x

        out = self.conv1(x)
        
        out = self.relu(out)
        out = self.bn1(out) #bn reverse
        
        # Chunk the feature map
        xs = torch.chunk(out, self.scale, dim=1)
        # Initialize output as empty tensor for proper concatenation
        y = 0
        for idx, conv in enumerate(self.convs):
            # Add previous y-value
            if self.first_block:
                y = xs[idx]
            else:
                y += xs[idx]
            y = conv(y)
            y = self.relu(self.bns[idx](y))
            # Concatenate with previously computed values
            out = torch.cat((out, y), 1) if idx > 0 else y
        # Use last chunk as x1
        if self.scale > 1:
            if self.first_block:
                out = torch.cat((out, self.pool(xs[len(self.convs)])), 1)
            else:
                out = torch.cat((out, xs[len(self.convs)]), 1)

        out = self.conv3(out)
        out = self.bn3(out)

        if self.downsample is not None:
            residual = self.downsample(x)

        out += residual
        out = self.relu(out)

        return out

def conv_layer(ni, nf, ks=3, stride=1, zero_bn=False, act=True):
    bn = nn.BatchNorm2d(nf)
    nn.init.constant_(bn.weight, 0. if zero_bn else 1.)
    if act:
        layers = [conv(ni, nf, ks, stride=stride), act_fn, bn]
    else:
        layers = [conv(ni, nf, ks, stride=stride), bn]
        
    
    #if act: layers.append(act_fn)
    return nn.Sequential(*layers)

class DecoderBlock(nn.Module):
    def __init__(self,
                 in_channels=512,
                 n_filters=256,
                 kernel_size=3,
                 is_deconv=False,
                 ):
        super().__init__()
        if kernel_size == 3:
            conv_padding = 1
        elif kernel_size == 1:
            conv_padding = 0
        # B, C, H, W -> B, C/4, H, W
        self.conv1 = nn.Conv2d(in_channels,
                               in_channels // 4,
                               kernel_size,
                               padding=1,bias=False)
        self.norm1 = nn.BatchNorm2d(in_channels // 4)
        self.relu1 = Mish()#nn.ReLU()
        # B, C/4, H, W -> B, C/4, H, W
        if is_deconv == True:
            self.deconv2 = nn.ConvTranspose2d(in_channels // 4,
                                              in_channels // 4,
                                              3,
                                              stride=2,
                                              padding=1,
                                              output_padding=conv_padding,bias=False)
        else:
            self.deconv2 = nn.Upsample(scale_factor=2, mode='bilinear', align_corners=True)
        self.norm2 = nn.BatchNorm2d(in_channels // 4)
        self.relu2 = Mish()#nn.ReLU()
        # B, C/4, H, W -> B, C, H, W
        self.conv3 = nn.Conv2d(in_channels // 4,
                               n_filters,
                               kernel_size,
                               padding=conv_padding,bias=False)
        self.norm3 = nn.BatchNorm2d(n_filters)
        self.relu3 = Mish()#nn.ReLU()
    def forward(self, x):
        x = self.conv1(x)
        x = self.relu1(x)
        x = self.norm1(x)
        x = self.deconv2(x)
        x = self.relu2(x)
        x = self.norm2(x)
        x = self.conv3(x)
        x = self.relu3(x)
        x = self.norm3(x)
        return x
class Res2Net_UNet(nn.Module):
    """Implements a Res2Net model as described in https://arxiv.org/pdf/1904.01169.pdf
    Args:
        block (torch.nn.Module): class constructor to be used for residual blocks
        layers (list<int>): layout of layers
        num_classes (int): number of output classes
        zero_init_residual (bool): whether the residual connections should be initialized at zero
        groups (int): number of convolution groups
        width_per_group (int): number of channels per group
        scale (int): scaling ratio within blocks
        replace_stride_with_dilation (list<bool>): whether stride should be traded for dilation
        norm_layer (torch.nn.Module): norm layer to be used
    """

    def __init__(self, block, layers, c_in=3,num_classes=2, zero_init_residual=False,
                 groups=1, width_per_group=26, scale=4, replace_stride_with_dilation=None,
                 norm_layer=None):
        super(Res2Net_UNet, self).__init__()
        if norm_layer is None:
            norm_layer = nn.BatchNorm2d
        self._norm_layer = norm_layer

        self.inplanes = 64
        self.dilation = 1
        
        if replace_stride_with_dilation is None:
            # each element in the tuple indicates if we should replace
            # the 2x2 stride with a dilated convolution instead
            replace_stride_with_dilation = [False, False, False]
        if len(replace_stride_with_dilation) != 3:
            raise ValueError("replace_stride_with_dilation should be None "
                             "or a 3-element tuple, got {}".format(replace_stride_with_dilation))
        self.groups = groups
        self.base_width = width_per_group
        self.scale = scale
        #self.conv1 = nn.Conv2d(3, self.inplanes, kernel_size=7, stride=2, padding=3,
        #                       bias=False)
        #modify stem
        #stem = []
        sizes = [c_in,32,64,64]  #modified per Grankin
        #for i in range(3):
        #    stem.append(conv_layer(sizes[i], sizes[i+1], stride=2 if i==0 else 1))
        
        #stem (initial entry layers)
        self.conv1 = conv_layer(c_in, sizes[1], stride=2)
        self.conv2 = conv_layer(sizes[1],sizes[2])
        self.conv3 = conv_layer(sizes[2],sizes[3])
        #self.conv1 = nn.Sequential(
        #    nn.Conv2d(3, 32, 3, 2, 1, bias=False),
        #    Mish(),
        #    nn.BatchNorm2d(32),
        #    nn.Conv2d(32, 32, 3, 1, 1, bias=False),
         #   Mish(),
         #   nn.BatchNorm2d(32),
         #   nn.Conv2d(32, 64, 3, 1, 1, bias=False)
       # )
        #nn.ReLU(inplace=True),
        #nn.ReLU(inplace=True),
        self.bn1 = nn.BatchNorm2d(64)
        self.relu = Mish()#nn.ReLU()
        
        
        
        self.maxpool = nn.MaxPool2d(kernel_size=3, stride=2, padding=1)
        
        #nn.MaxPool2d(kernel_size=3, stride=2, padding=1)
        self.layer1 = self._make_layer(block, 64, layers[0])
        self.layer2 = self._make_layer(block, 128, layers[1], stride=2,
                                       dilate=replace_stride_with_dilation[0])
        self.layer3 = self._make_layer(block, 256, layers[2], stride=2,
                                       dilate=replace_stride_with_dilation[1])
        self.layer4 = self._make_layer(block, 512, layers[3], stride=2,
                                       dilate=replace_stride_with_dilation[2])
        self.avgpool = nn.AdaptiveAvgPool2d((1, 1))
        #self.fc = nn.Linear(512 * block.expansion, num_classes)
        
        filters = [64, 128, 256, 512]
        is_deconv=False
        decoder_kernel_size=3
        self.base_size=512
        self.crop_size=512
        self._up_kwargs={'mode': 'bilinear', 'align_corners': True}
        # Decoder
        #in_channels=filters[3],
        self.center = DecoderBlock(in_channels=filters[3]*4,
                                   n_filters=filters[3],
                                   kernel_size=decoder_kernel_size,
                                   is_deconv=is_deconv)
        self.decoder4 = DecoderBlock(in_channels=filters[3] + filters[2]*4,
                                     n_filters=filters[2],
                                     kernel_size=decoder_kernel_size,
                                     is_deconv=is_deconv)
        self.decoder3 = DecoderBlock(in_channels=filters[2] + filters[1]*4,
                                     n_filters=filters[1],
                                     kernel_size=decoder_kernel_size,
                                     is_deconv=is_deconv)
        self.decoder2 = DecoderBlock(in_channels=filters[1] + filters[0]*4,
                                     n_filters=filters[0],
                                     kernel_size=decoder_kernel_size,
                                     is_deconv=is_deconv)
        self.decoder1 = DecoderBlock(in_channels=filters[0] + filters[0],
                                     n_filters=filters[0],
                                     kernel_size=decoder_kernel_size,
                                     is_deconv=is_deconv)
 
 
        self.finalconv = nn.Sequential(nn.Conv2d(filters[0], 32, 3, padding=1, bias=False),
                                       nn.BatchNorm2d(32),
                                       Mish(),
                                       nn.Dropout2d(0.1, False),
                                       nn.Conv2d(32, num_classes, 1))
                                       #nn.ReLU()

        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)

        # Zero-initialize the last BN in each residual branch,
        # so that the residual branch starts with zeros, and each residual block behaves like an identity.
        # This improves the model by 0.2~0.3% according to https://arxiv.org/abs/1706.02677
        if zero_init_residual:
            for m in self.modules():
                if isinstance(m, Bottle2neck):
                    nn.init.constant_(m.bn3.weight, 0)
                elif isinstance(m, BasicBlock):
                    nn.init.constant_(m.bn2.weight, 0)

    def _make_layer(self, block, planes, blocks, stride=1, dilate=False):
        norm_layer = self._norm_layer
        downsample = None
        previous_dilation = self.dilation
        if dilate:
            self.dilation *= stride
            stride = 1
        if stride != 1 or self.inplanes != planes * block.expansion:
            downsample = nn.Sequential(
                conv1x1(self.inplanes, planes * block.expansion, stride),
                norm_layer(planes * block.expansion),
            )

        layers = []
        layers.append(block(self.inplanes, planes, stride, downsample, self.groups,
                            self.base_width, previous_dilation, self.scale, first_block=True, norm_layer=norm_layer))
        self.inplanes = planes * block.expansion
        for _ in range(1, blocks):
            layers.append(block(self.inplanes, planes, groups=self.groups,
                                base_width=self.base_width, dilation=self.dilation,
                                scale=self.scale, first_block=False, norm_layer=norm_layer))

        return nn.Sequential(*layers)

    def forward(self, x):
        
        #stem layers
        x = self.conv1(x)
        x = self.conv2(x)
        x = self.conv3(x)
        #x = self.conv1(x)
        #x = self.relu(x)
        #x = self.bn1(x)
        x_ = self.maxpool(x)
       
        #res2 block layers
        x1 = self.layer1(x_)
        x2 = self.layer2(x1)
        x3 = self.layer3(x2)
        x4 = self.layer4(x3)
        
        center = self.center(x4)
 
        d4 = self.decoder4(torch.cat([center, x3], 1))
        d3 = self.decoder3(torch.cat([d4, x2], 1))
        d2 = self.decoder2(torch.cat([d3, x1], 1))
        d1 = self.decoder1(torch.cat([d2, x], 1))
 
        f= self.finalconv(d1)
        return f

#26 s=4
def res2net_plus(depth=50, num_classes=2, width_per_group=26, scale=4, pretrained=False, progress=True, **kwargs):
    """Instantiate a Res2Net model
    Args:
        depth (int): depth of the model
        num_classes (int): number of output classes
        scale (int): number of branches for cascade convolutions
        pretrained (bool): whether the model should load pretrained weights (ImageNet training)
        progress (bool): whether a progress bar should be displayed while downloading pretrained weights
        **kwargs: optional arguments of torchvision.models.resnet.ResNet
    Returns:
        model (torch.nn.Module): loaded Pytorch model
    """

    if RESNET_LAYERS.get(depth) is None:
        raise NotImplementedError(f"This specific architecture is not defined for that depth: {depth}")

    block = Res2Block if depth >= 50 else BasicBlock

    model = Res2Net_UNet(block, [3, 4, 6, 3], num_classes=num_classes, scale=scale, **kwargs)

    if pretrained:
        state_dict = torch.load('/home/boyu/Res2Net/pretrained/res2net50_v1b_26w_4s-3cf99910.pth')
        # Remove FC params from dict
        del state_dict['fc.weight']
        del state_dict['fc.bias']
        
       
        missing, unexpected = model.load_state_dict(state_dict, strict=False)
        

        if any(unexpected) or any(not elt.startswith('fc.') for elt in missing):
            raise KeyError(f"Weight loading failed.\nMissing parameters: {missing}\nUnexpected parameters: {unexpected}")


    return model


def res2next(depth, num_classes, width_per_group=4, scale=4, pretrained=False, progress=True, **kwargs):
    """Instantiate a Res2NeXt model
    Args:
        depth (int): depth of the model
        num_classes (int): number of output classes
        scale (int): number of branches for cascade convolutions
        pretrained (bool): whether the model should load pretrained weights (ImageNet training)
        progress (bool): whether a progress bar should be displayed while downloading pretrained weights
        **kwargs: optional arguments of torchvision.models.resnet.ResNet
    Returns:
        model (torch.nn.Module): loaded Pytorch model
    """

    if RESNET_LAYERS.get(depth) is None:
        raise NotImplementedError(f"This specific architecture is not defined for that depth: {depth}")

    block = Res2Block if depth >= 50 else BasicBlock

    kwargs.update(RES2NEXT_PARAMS.get(depth))
    model = Res2Net_UNet(block, RESNET_LAYERS.get(depth), num_classes=num_classes, scale=scale, **kwargs)

    if pretrained:
        state_dict = load_state_dict_from_url(URLS.get(f"res2next{depth}_{width_per_group}w_{scale}s_{kwargs['groups']}c"), progress=progress)
        # Remove FC params from dict
        del state_dict['fc.weight']
        del state_dict['fc.bias']
        missing, unexpected = model.load_state_dict(state_dict, strict=False)

        if any(unexpected) or any(not elt.startswith('fc.') for elt in missing):
            raise KeyError(f"Weight loading failed.\nMissing parameters: {missing}\nUnexpected parameters: {unexpected}")

    return model
    
if __name__ == '__main__':
    images = torch.rand(1, 3, 512, 512).cuda(0)
    model = res2net_plus(pretrained=False)
    model = model.cuda(0)
    print(model(images).size())
