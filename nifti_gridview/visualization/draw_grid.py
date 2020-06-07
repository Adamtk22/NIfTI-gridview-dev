from torchvision.utils import make_grid
from torch import tensor, nn
import numpy as np
import cv2

colormaps = {
    'Default': None,
    'Parula': cv2.COLORMAP_PARULA,
    'Autumn': cv2.COLORMAP_AUTUMN,
    'Bone': cv2.COLORMAP_BONE,
    'Jet': cv2.COLORMAP_JET,
    'Rainbow': cv2.COLORMAP_RAINBOW,
    'Ocean': cv2.COLORMAP_OCEAN,
    'Summer': cv2.COLORMAP_SUMMER,
    'Spring': cv2.COLORMAP_SPRING,
    'Cool': cv2.COLORMAP_COOL ,
    'HSV': cv2.COLORMAP_HSV,
    'Pink': cv2.COLORMAP_PINK,
    'Hot': cv2.COLORMAP_HOT
}

def draw_grid(image, crop=None, nrow=None, offset=None, background=0, margins=1, cmap=None, **kwargs):
    """
    This is the wrapper function for make_grid that supports some extra tweaking.

    Args:
        image (np.ndarray or torch.Tensor):
            Input 3D image, should have a dimension of 3 with configuration Z x W x H.
        crop (dict, Optional):
            If provided with key `{'center': [w, h] 'size': [sw, sh] or int }`, the image is cropped
            first before making the grid. Default to None.
        nrow (int, Optional):
            Passed to function `make_grid`. Automatically calculated if its None to be the square
            root of total number of input slices in `image`. Default to None.
        offset (int, Optional):
            Offset the input along Z-direction by inserting empty slices. Default to None.
        background (float, Optional)
            Background pixel value for offset and margins option. Default to 0.
        margins (int, Optional):
            Pass to `make_grid` padding option. Default to 1.
        cmap (str, Optional):
            Colormap for image drawing, see dicitonary `cmap` for a list of available colormap. Default
            to `None`.
        **kwargs:
            Not suppose to have any use.

    Returns:
        torch.Tensor
    """
    assert offset >= 0 or offset is None, "In correct offset setting!"


    if isinstance(image, np.ndarray):
        try:
            image = tensor(image)
        except:
            image = tensor(image.astype('int32'))

    # Offset the image by padding zeros
    if not offset is None:
        image = image.squeeze()
        image = nn.ConstantPad3d((0, 0, 0, 0, offset, 0), 0)(image)

    # Handle dimensions
    if image.dim() == 3:
        image = image.unsqueeze(1)

    # compute number of image per row if now provided
    if nrow is None:
        nrow = np.int(np.ceil(np.sqrt(len(image))))


    # Crop the image along the x, y direction, ignore z direction.
    if not crop is None:
        # Find center of mass for segmentation
        im_shape = image.shape

        center = crop['center']
        size = crop['size']
        lower_bound = [np.max([0, int(c - s // 2)]) for c, s in zip(center, size)]
        upper_bound = [np.min([l + s, m]) for l, s, m in zip(lower_bound, size, im_shape[1:])]

        # Crop
        image = image[:,:, lower_bound[0]:upper_bound[0], lower_bound[1]:upper_bound[1]]

    if nrow is None:
        nrow = int(np.round(np.sqrt(image.shape[0])))

    # return image as RGB with range 0 to 255
    im_grid = make_grid(image, nrow=nrow, padding=margins, normalize=True, pad_value=background)
    im_grid = (im_grid * 255.).permute(1, 2, 0).numpy().astype('uint8').copy()

    if not (cmap is None or cmap == 'Default'):
        im_grid = cv2.applyColorMap(im_grid[:,:,0], colormaps[cmap])

    # im_grid = (im_grid).permute(1, 2, 0).numpy().astype('float').copy()
    return im_grid

def draw_grid_contour(im_grid, seg, crop=None, nrow=None, offset=None, background=0, margins=1, color=None,
                      thickness=2, **kwargs):
    """
    This is the wrapper function for make_grid that supports some extra tweaking.

    Args:
        seg (np.ndarray or torch.Tensor):
            Input 3D image, should have a dimension of 3 with configuration Z x W x H.
        crop (dict, Optional):
            If provided with key `{'center': [w, h] 'size': [sw, sh] or int }`, the image is cropped
            first before making the grid. Default to None.
        nrow (int, Optional):
            Passed to function `make_grid`. Automatically calculated if its None to be the square
            root of total number of input slices in `image`. Default to None.
        offset (int, Optional):
            Offset the input along Z-direction by inserting empty slices. Default to None.
        background (float, Optional)
            Background pixel value for offset and margins option. Default to 0.
        margins (int, Optional):
            Pass to `make_grid` padding option. Default to 1.
        color (iter, Optional):
            Color of the output contour.
        **kwargs:
            Not suppose to have any use.

    Returns:
        torch.Tensor
    """
    assert offset >= 0 or offset is None, "In correct offset setting!"


    if isinstance(seg, np.ndarray):
        seg = tensor(seg.astype('uint8'))

    # Offset the image by padding zeros
    if not offset is None:
        seg = seg.squeeze()
        seg = nn.ConstantPad3d((0, 0, 0, 0, offset, 0), 0)(seg)

    # Handle dimensions
    if seg.dim() == 3:
        seg = seg.unsqueeze(1)

    # compute number of image per row if now provided
    if nrow is None:
        nrow = np.int(np.ceil(np.sqrt(len(seg))))


    # Crop the image along the x, y direction, ignore z direction.
    if not crop is None:
        # Find center of mass for segmentation
        seg_shape = seg.shape

        center = crop['center']
        size = crop['size']
        lower_bound = [np.max([0, int(c - s // 2)]) for c, s in zip(center, size)]
        upper_bound = [np.min([l + s, m]) for l, s, m in zip(lower_bound, size, seg_shape[1:])]

        # Crop
        seg = seg[:,:, lower_bound[0]:upper_bound[0], lower_bound[1]:upper_bound[1]]

    if nrow is None:
        nrow = int(np.round(np.sqrt(seg.shape[0])))

    # return image as RGB with range 0 to 255
    seg_grid = make_grid(seg, nrow=nrow, padding=margins, normalize=False, pad_value=background)
    seg_grid = seg_grid[0].numpy().astype('uint8').copy()

    # Find Contours
    _a, contours, _b = cv2.findContours(seg_grid, mode=cv2.RETR_EXTERNAL,
                                        method=cv2.CHAIN_APPROX_SIMPLE)

    # Draw contour on image grid
    try:
        cv2.drawContours(im_grid, contours, -1, color.color().getRgb()[:3], thickness=thickness)
    except Exception as e:
        print(e)
    return im_grid