import torch
import torch.nn as nn
import torch.nn.init as init
import torch.nn.functional as functional
from typing import Union

# ------------------------------------------------------------------------------
# One-dimensional Convolution Gated Recurrent Unit
# ------------------------------------------------------------------------------


class ConvGRU1DCell(nn.Module):

    # --------------------------------------------------------------------------
    # Initialization
    # --------------------------------------------------------------------------
    
    def __init__(self, input_channels: int, hidden_channels: int, 
                 kernel_size: int, stride: int=1, padding: int=0,
                 recurrent_kernel_size: int=3):
        """
        One-Dimensional Convolutional Gated Recurrent Unit (ConvGRU1D) cell.

        The input-to-hidden convolution kernel can be defined arbitrarily using
        the kernel_size, stride and padding parameters. The hidden-to-hidden
        convolution kernel is forced to be unit-stride, with a padding assuming
        an odd kernel size, in order to keep the number of features the same.
        
        The hidden state is initialized by default to a zero tensor of the
        appropriate shape.

        Arguments:
            input_channels {int} -- [Number of channels of the input tensor]
            hidden_channels {int} -- [Number of channels of the hidden state]
            kernel_size {int} -- [Size of the input-to-hidden convolving kernel]
        
        Keyword Arguments:
            stride {int} -- [Stride of the input-to-hidden convolution] 
                             (default: {1})
            padding {int} -- [Zero-padding added to both sides of the input] 
                              (default: {0})
            recurrent_kernel_size {int} -- [Size of the hidden-to-hidden 
                                            convolving kernel] (default: {3})
        """
        super(ConvGRU1DCell, self).__init__()
        
        self.conv_ih = nn.Conv1d(input_channels, hidden_channels * 3, 
                                 kernel_size, stride=stride, padding=padding)
        self.conv_hh = nn.Conv1d(hidden_channels, hidden_channels * 3, 
                                 recurrent_kernel_size, stride=1, 
                                 padding=recurrent_kernel_size // 2)
        self.h_channels = hidden_channels
    
        self.reset_parameters()

    def reset_parameters(self):
        init.orthogonal_(self.conv_hh.weight)
        init.xavier_uniform_(self.conv_ih.weight)
        init.zeros_(self.conv_hh.bias)
        init.zeros_(self.conv_ih.bias)

    # --------------------------------------------------------------------------
    # Processing
    # --------------------------------------------------------------------------
    
    def forward(self, input, hx=None):
        output_size = \
            int((input.size(-1) - self.conv_ih.kernel_size[0] + 
                 2 * self.conv_ih.padding[0]) / self.conv_ih.stride[0]) + 1
        # Handle the case of no hidden state provided
        if hx is None:
            hx = torch.zeros(input.size(0), self.h_channels, output_size, 
                             device=input.device)
        # Run the input->hidden and hidden->hidden convolution kernels
        ih_conv_output = self.conv_ih(input)
        hh_conv_output = self.conv_hh(hx)
        # Separate the results and apply Gated Recurrent Unit equations
        z = torch.sigmoid(ih_conv_output[:, :self.h_channels, :] + 
                          hh_conv_output[:, :self.h_channels, :])
        r = torch.sigmoid(
            ih_conv_output[:, self.h_channels:2*self.h_channels, :] + 
            hh_conv_output[:, self.h_channels:2*self.h_channels, :])
        n = torch.tanh(ih_conv_output[:, 2*self.h_channels:, :] + 
                       r * hh_conv_output[:, 2*self.h_channels:, :])
        return (1 - z) * n + z * hx

# ------------------------------------------------------------------------------
# Two-dimensional Convolution Gated Recurrent Unit
# ------------------------------------------------------------------------------


class ConvGRU2DCell(nn.Module):

    # --------------------------------------------------------------------------
    # Initialization
    # --------------------------------------------------------------------------
    
    def __init__(self, input_channels: int, hidden_channels: int, 
                 kernel_size: Union[int, tuple], 
                 stride: Union[int, tuple]=(1, 1), 
                 padding: Union[int, tuple]=(0, 0),
                 recurrent_kernel_size: Union[int, tuple]=(3, 3)):
        """
        Two-Dimensional Convolutional Gated Recurrent Unit (ConvGRU2D) cell.
        
        The input-to-hidden convolution kernel can be defined arbitrarily using
        the kernel_size, stride and padding parameters. The hidden-to-hidden
        convolution kernel is forced to be unit-stride, with a padding assuming
        an odd kernel size in both dimensions, in order to keep the number of 
        features the same.
        
        The hidden state is initialized by default to a zero tensor of the
        appropriate shape.

        Arguments:
            input_channels {int} -- [Number of channels of the input tensor]
            hidden_channels {int} -- [Number of channels of the hidden state]
            kernel_size {int or tuple} -- [Size of the input-to-hidden 
                                           convolving kernel]
        
        Keyword Arguments:
            stride {int or tuple} -- [Stride of the input-to-hidden convolution] 
                                      (default: {(1, 1)})
            padding {int or tuple} -- [Zero-padding added to both sides of the 
                                       input] (default: {0})
            recurrent_kernel_size {int or tuple} -- [Size of the hidden-to-
                                                     -hidden convolving kernel] 
                                                     (default: {(3, 3)})
        """
        super(ConvGRU2DCell, self).__init__()

        hh_padding = (recurrent_kernel_size[0] // 2, 
                      recurrent_kernel_size[1] // 2)
        
        self.conv_ih = nn.Conv2d(input_channels, hidden_channels * 3, 
                                 kernel_size, stride=stride, padding=padding)
        self.conv_hh = nn.Conv2d(hidden_channels, hidden_channels * 3, 
                                 recurrent_kernel_size, stride=1, 
                                 padding=hh_padding)
        self.h_channels = hidden_channels
    
        self.reset_parameters()

    def reset_parameters(self):
        init.orthogonal_(self.conv_hh.weight)
        init.xavier_uniform_(self.conv_ih.weight)
        init.zeros_(self.conv_hh.bias)
        init.zeros_(self.conv_ih.bias)
    
    # --------------------------------------------------------------------------
    # Processing
    # --------------------------------------------------------------------------
    
    def forward(self, input, hx=None):
        output_size = \
            (int((input.size(-2) - self.conv_ih.kernel_size[0] + 
             2 * self.conv_ih.padding[0]) / self.conv_ih.stride[0]) + 1, 
            int((input.size(-1) - self.conv_ih.kernel_size[1] + 
             2 * self.conv_ih.padding[1]) / self.conv_ih.stride[1]) + 1)
        # Handle the case of no hidden state provided
        if hx is None:
            hx = torch.zeros(input.size(0), self.h_channels, *output_size, 
                             device=input.device)
        # Run the input->hidden and hidden->hidden convolution kernels
        ih_conv_output = self.conv_ih(input)
        hh_conv_output = self.conv_hh(hx)
        # Separate the results and apply Gated Recurrent Unit equations
        z = torch.sigmoid(ih_conv_output[:, :self.h_channels, :, :] + 
                          hh_conv_output[:, :self.h_channels, :, :])
        r = torch.sigmoid(
            ih_conv_output[:, self.h_channels:2*self.h_channels, :, :] + 
            hh_conv_output[:, self.h_channels:2*self.h_channels, :, :])
        n = torch.tanh(ih_conv_output[:, 2*self.h_channels:, :, :] + 
                       r * hh_conv_output[:, 2*self.h_channels:, :, :])
        return (1 - z) * n + z * hx
