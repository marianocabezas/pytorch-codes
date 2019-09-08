from __future__ import division
import numpy as np
import torch
import torch.nn.functional as F


def gaussian_mse(pred, target, intervals=[0., 300., 450., np.inf], alpha=3.):
    intervals = torch.tensor(intervals).to(pred.device)
    max_a = map(lambda t: torch.min(intervals[intervals >= t]), target)
    min_a = map(lambda t: torch.max(intervals[intervals < t]), target)
    a = torch.tensor(
        map(
            lambda (min_i, max_i, t): min(max_i - t, t - min_i) / alpha,
            zip(min_a, max_a, target)
        )
    ).to(pred.device)
    mse = 1 - torch.exp(- (pred - target) * (pred - target) / a)

    return torch.sum(mse)


def normalised_mse(pred, target, norm_rate=1):
    diff = (target - pred)
    sq_diff = diff * diff
    max_diff = torch.max(sq_diff) * norm_rate
    return torch.mean(sq_diff) / max_diff

def multidsc_loss(pred, target, smooth=1, averaged=True):
    """
    Loss function based on a multi-class DSC metric.
    :param pred: Predicted values. This tensor should have the shape:
     [batch_size, n_classes, data_shape]
    :param target: Ground truth values. This tensor can have multiple shapes:
     - [batch_size, n_classes, data_shape]: This is the expected output since
       it matches with the predicted tensor.
     - [batch_size, data_shape]: In this case, the tensor is labeled with
       values ranging from 0 to n_classes. We need to convert it to
       categorical.
    :param smooth: Parameter used to smooth the DSC when there are no positive
     samples.
    :param averaged: Parameter to decide whether to return the average DSC or
     a tensor with the different class DSC values.
    :return: The mean DSC for the batch
    """
    dims = pred.shape
    n_classes = dims[1]
    if target.shape != dims:
        assert torch.max(target) <= n_classes, 'Wrong number of classes for GT'
        if len(target.shape) == len(pred.shape):
            target = torch.cat(
                map(lambda i: target == i, range(n_classes)), dim=1
            )
        else:
            target = torch.stack(
                map(lambda i: target == i, range(n_classes)), dim=1
            )

    target = target.type_as(pred)

    reduce_dims = tuple(range(1, len(dims)))
    num = (2 * torch.sum(pred * target, dim=reduce_dims[1:])) + smooth
    den = torch.sum(pred + target, dim=reduce_dims[1:]) + smooth
    dsc_k = num / den
    if averaged:
        dsc = 1 - torch.mean(dsc_k)
    else:
        dsc = 1 - torch.mean(dsc_k, dim=0)

    return torch.clamp(dsc, 0., 1.)


class GenericLossLayer(torch.nn.Module):
    def __init__(self, func_handle):
        super(GenericLossLayer, self).__init__()
        self.func = func_handle

    def forward(self, pred, target):
        return self.func(pred, target)
