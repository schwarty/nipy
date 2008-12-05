"""
An implementation of the dimension info as desribed in 

http://nifti.nimh.nih.gov/pub/dist/src/niftilib/nifti1.h

In particular, it allows one to check if a `CoordinateMap` instance
can be coerced into a valid NIFTI CoordinateMap instance. For a 
valid NIFTI coordmap, we can then ask which axes correspond to time,
slice, phase and frequency.

Axes:
-----

NIFTI files can have up to seven dimensions. We take the convention that
the output coordinate names are ['x','y','z','t','u','v','w']
and the input coordinate names are ['i','j','k','l','m','n','o'].

In the NIFTI specification, the order of the output coordinates (at least the 
first 3) are fixed to be ['x','y','z'] and their order is not mean to change. 
As for input coordinates, the first three can be reordered, so 
['j','k','i','l'] is valid, for instance.

NIFTI has a 'diminfo' header attribute that optionally specifies the
order of the ['i', 'j', 'k'] axes. To use similar
terms to those in the nifti1.h header, 'phase' corresponds to 'i';
'frequency' to 'j' and 'slice' to 'k'. We use ['i','j','k'] instead because
there are images for which the terms 'phase' and 'frequency' have no proper
meaning. See the functions `get_freq_axes`, `get_phase_axis` for how this
is dealt with.

Voxel coordinates:
------------------

NIFTI's voxel convention is what can best be described as 0-based
FORTRAN indexing (confirm this). For example: suppose we want the
x=20-th, y=10-th pixel of the third slice of an image with 30 64x64 slices. This

>>> nifti_ijk = [19,9,2]
>>> d = np.load('data.img', dtype=np.float, shape=(30,64,64))
>>> request = d[nifti_ijk[::-1]]

FIXME: For this reason, we have to consider whether we should transpose the
memmap from pynifti. 
"""

import warnings
from string import join

import numpy as np

from neuroimaging.core.api import CoordinateSystem, Affine, CoordinateMap, VoxelCoordinateSystem

valid_input = list('ijklmno') # (i,j,k) = ('phase', 'frequency', 'slice')
valid_output = list('xyztuvw')

def reverse_input(coordmap):
    """
    Create a new coordmap with reversed input_coords.

    Inputs:
    -------
    coordmap: `CoordinateMap`

    Returns:
    --------

    newcoordmap: `CoordinateMap`
         a new CoordinateMap with reversed input_coords.
    """
    newaxes = coordmap.input_coords.axes()[::-1]
    newincoords = VoxelCoordinateSystem(coordmap.input_coords.name + '-reordered',
                                   newaxes)
    
    ndim = coordmap.ndim[0]
    perm = np.zeros((ndim+1,)*2)
    perm[-1,-1] = 1.

    for i, j in enumerate(transpose):
        perm[i,ndim-1-i] = 1.

    return CoordinateMap(Affine(A), newincoords, coordmap.output_coords.copy())

def reverse_output(coordmap):
    """
    Create a new coordmap with reversed output_coords.

    Inputs:
    -------
    coordmap: `CoordinateMap`

    Returns:
    --------

    newcoordmap: `CoordinateMap`
         a new CoordinateMap with reversed output_coords.
    """
    newaxes = coordmap.input_coords.axes()[::-1]
    newincoords = VoxelCoordinateSystem(coordmap.input_coords.name + '-reordered',
                                   newaxes)
    
    ndim = coordmap.ndim[0]
    perm = np.zeros((ndim+1,)*2)
    perm[-1,-1] = 1.

    for i, j in enumerate(transpose):
        perm[i,ndim-1-i] = 1.

    return CoordinateMap(Affine(A), newincoords, coordmap.output_coords.copy())



def coerce_coordmap(coordmap):
    """
    Determine if a given CoordinateMap instance can be used as 
    a valid coordmap for a NIFTI image, so that an Image can be saved.

    If the input coordinates must be reordered, the order defaults
    to the NIFTI order ['i','j','k','l','m','n','o'].

    Inputs:
    -------

    coordmap: `CoordinateMap`

    Returns: (newcmap, transp_order)
    --------

    newcmap: `CoordinateMap`
           a new CoordinateMap that can be used with a (possibly
           transposed array) in a proper Image. 

    transp_order: `list`
           a list that should be used to transpose any Image
           with this coordmap to allow it to be saved as NIFTI

    """

    if not hasattr(coordmap, 'affine'):
        raise ValueError, 'coordmap must be affine to save as a NIFTI file'

    affine = coordmap.affine
    if affine.shape[0] != affine.shape[1]:
        raise ValueError, 'affine must be square to save as a NIFTI file'

    ndim = affine.shape[0] - 1
    inaxes = coordmap.input_coords.axisnames()
    vinput = valid_input[:ndim]
    if set(vinput) != set(inaxes):
        raise ValueError, 'input coordinate axisnames of a %d-dimensional Image must come from %s' % (ndim, `vinput`)

    voutput = valid_output[:ndim]
    outaxes = coordmap.output_coords.axisnames()
    if set(voutput) != set(outaxes):
        raise ValueError, 'output coordinate axisnames of a %d-dimensional Image must come from %s' % (ndim, `voutput`)

    # if the input coordinates do not have the proper order,
    # the image would have to be transposed to be saved
    # the i,j,k can be in any order in the first 
    # three slots, but the remaining ones
    # should be in order because there is no NIFTI
    # header attribute that can tell us
    # anything about this order. also, the NIFTI header says that
    # the phase, freq, slice values all have to be less than 3

    reinput = False
    if inaxes != vinput:
        ndimm = min(ndim, 3)
        if set(inaxes[:ndimm]) != set(vinput[:ndimm]):
            warnings.warn('an Image with this coordmap has to be transposed to be saved because the first three input axes are not from %s' % `set(vinput[:ndimm])`)
            reinput = True
        if inaxes[ndimm:] != vinput[ndimm:]:
            warnings.warn('an Image with this coordmap has to be transposed because the last %d axes are not in the NIFTI order' % (ndim-3,))
            reinput = True

    # if the output coordinates are not in the NIFTI order,
    # they will have to be put in NIFTI order, affecting
    # the affine matrix

    reoutput = False
    if outaxes != voutput:
        warnings.warn('The order of the output coordinates is not the NIFTI order, this will change the affine transformation by reordering the output coordinates.')
        reoutput = True

    # Create the appropriate reorderings, if necessary

    inperm = np.identity(ndim+1)
    if reinput:
        inperm[:ndim,:ndim] = np.array([[int(vinput[i] == inaxes[j]) 
                                      for j in range(ndim)] 
                                     for i in range(ndim)])
    intrans = tuple(np.dot(inperm, range(ndim+1)).astype(np.int))[:-1]

    outperm = np.identity(ndim+1)
    if reoutput:
        outperm[:ndim,:ndim] = np.array([[int(voutput[i] == outaxes[j]) 
                                       for j in range(ndim)] 
                                      for i in range(ndim)])
    outtrans = tuple(np.dot(outperm, range(ndim+1)).astype(np.int))[:-1]

    # Create the new affine

    A = np.dot(outperm, np.dot(affine, inperm))

    # If the affine beyond the 3 coordinate is not diagonal
    # some information will be lost saving to NIFTI

    if not np.allclose(np.diag(np.diag(A))[3:,3:], A[3:,3:]):
        warnings.warn("the affine is not diagonal in the non 'ijk','xyz' coordinates, information will be lost in saving to NIFTI")
        
    # Create new coordinate systems

    if not np.allclose(inperm, np.identity(ndim+1)):
        inname = coordmap.input_coords.name + '-reordered'
    else:
        inname = coordmap.input_coords.name

    if not np.allclose(outperm, np.identity(ndim+1)):
        outname = coordmap.output_coords.name + '-reordered'
    else:
        outname = coordmap.output_coords.name

    axes = coordmap.input_coords.axes()
    newincoords = VoxelCoordinateSystem(inname, [axes[i] for i in intrans])

    axes = coordmap.output_coords.axes()
    newoutcoords = CoordinateSystem(outname, [axes[i] for i in outtrans])

    return CoordinateMap(Affine(A), newincoords, newoutcoords), intrans

def get_pixdim(coordmap):
    """
    Get pixdim from a coordmap, after validating
    it as a valid NIFTI coordmap. The pixdims 
    are taken from the output_coords. Specifically, 
    for each axis 'xyztuvw', if the corresponding
    output_coord has a step, use it, otherwise use 0.

    Inputs:
    -------
    coordmap: `CoordinateMap`

    Returns:
    --------
    pixdim: np.ndarray(dtype=np.float)
           non-negative pixdim values to be saved as NIFTI

    """

    # NIFTI header specifies pixdim should be positive (we take this
    # as non-negative).
    # since we will save the actual 4x4 affine in the NIFTI header,
    # we set the spatial pixdims to 0, UNLESS the corresponding
    # coordmap.output_coords.axes() using
    # the NIFTI order 'xyztuvw', i.e. the pixdim
    # order comes from the OUTPUT coordinates and should
    # always represent 'xyztuvw' and not necessarily know anything
    # about the 'ijklmno' order

    ndim = coordmap.ndim[0]
    newcmap, _ = coerce_coordmap(coordmap)
    pixdim = np.zeros(ndim)
    for i, l in enumerate('xyztuvw'[:ndim]):
        ll = coordmap.output_coords[l]
        if hasattr(ll, 'step'):
            pixdim[i] = ll.step

    if not np.alltrue(np.greater_equal(pixdim, 0)):
        warnings.warn("NIFTI expectes non-negative pixdims, taking absolute value")
    A = newcmap.affine
    opixdim = np.diag(A)[3:-1]
    if not np.allclose(opixdim, pixdim[3:]):
        warnings.warn("pixdims from output_coords:%s, do not agree with pixdim from (coerced) affine matrix:%s. using those from output_coords" % (`pixdim[3:]`, `opixdim`))


    return np.fabs(pixdim)

def get_diminfo(coordmap):
    """
    Get diminfo byte from a coordmap, after validating it as a
    valid NIFTI coordmap.

    Inputs:
    -------
    coordmap: `CoordinateMap`

    Returns:
    --------
    nifti_diminfo: int
           a valid NIFIT diminfo value, based on the order
           of i(='phase'), j(='freq'), k(='slice') in the
           input_coords of newcmap
           
    Notes:
    ------
    This is the diminfo of the REORDERED  (if necessary) coordmap

    """

    newcoordmap, _ = coerce_coordmap(coordmap)

    ii, jj, kk = [newcoordmap.input_coords.axisnames().index(l) for l in 'ijk']
    return _diminfo_from_fps(ii, jj, kk)

def ijk_from_diminfo(diminfo):
    """
    Determine the order of the 'ijk' dimensions from the diminfo byte
    of a NIFTI header. If any of them are 'undefined', set the order
    alphabetically, after having set the ones that are defined.
    
    Inputs:
    -------
    diminfo: int

    Returns:
    --------
    ijk: str
         A string reflecting the order of the 'ijk' coordinates. 
         
    Notes:
    ------
    Because the 'k' coordinate is the slice coordinate axis in NIFTI,
    where 'k' is in the string determines the slice axis.

    """
    i, j, k = _fps_from_diminfo(diminfo)
    out = list('aaa')
    if i >= 0: out[i] = 'i'
    if j >= 0: out[j] = 'j'
    if k >= 0: out[k] = 'k'

    remaining = list(set('ijk').difference(set(out)))
    remaining.sort()
    used = filter(lambda x: x >= 0, (i,j,k))

    for l in range(3):
        if l not  in used:
            out[l] = remaining.pop(0)
    return join(out, '')

def get_slice_axis(coordmap):
    """
    Determine the slice axis of a valid NIFTI coordmap.

    Inputs:
    -------
    coordmap: `CoordinateMap`

    Returns: 
    --------
    axis: which axis of the array corresponds to 'slice'
    """
    coerce_coordmap(coordmap)
    return coordmap.input_coords.axisnames().index('k')

def get_time_axis(coordmap):
    """
    Determine the time axis of a valid NIFTI coordmap.

    Inputs:
    -------
    coordmap: `CoordinateMap`

    Returns: 
    --------
    axis: which axis of the array corresponds to 'time'

    """
    coerce_coordmap(coordmap)
    return coordmap.input_coords.axisnames().index('l')

def get_freq_axis(coordmap):
    """
    Determine the freq axis of a valid NIFTI coordmap.

    Inputs:
    -------
    coordmap: `CoordinateMap`

    Returns: 
    --------
    axis: which axis of the array corresponds to 'time'

    Notes:
    ------
    As described in nifti1.h, 'frequency' axis may not make sense for 
    some pulse sequences (i.e. spin gradient). This function returns
    the axis of 'j' in the NIFTI coordmap, which corresponds to 
    'frequency' if it is defined in the diminfo byte of a NIFTI header.
    """
    coerce_coordmap(coordmap)
    return coordmap.input_coords.axisnames().index('j')

def get_phase_axis(coordmap):
    """
    Determine the freq axis of a valid NIFTI coordmap.

    Inputs:
    -------
    coordmap: `CoordinateMap`

    Returns: 
    --------
    axis: which axis of the array corresponds to 'time'

    Notes:
    ------
    As described in nifti1.h, 'phase' axis may not make sense for 
    some pulse sequences (i.e. spin gradient). This function returns
    the axis of 'i' in the NIFTI coordmap, which corresponds to 
    'phase' if it is defined in the diminfo byte of a NIFTI header.
    """
    coerce_coordmap(coordmap)
    return coordmap.input_coords.axisnames().index('i')


def _fps_from_diminfo(diminfo):
    """
    Taken from nifti1.h

    #define DIM_INFO_TO_FREQ_DIM(di)   ( ((di)     ) & 0x03 )
    #define DIM_INFO_TO_PHASE_DIM(di)  ( ((di) >> 2) & 0x03 )
    #define DIM_INFO_TO_SLICE_DIM(di)  ( ((di) >> 4) & 0x03 )

    Because NIFTI expects values from 1-3 with 0 being 'undefined',
    we have to subtract 1 from each, making a return value of -1 'undefined'
    """
    f = int(diminfo) & 0x03 
    p = int(diminfo >> 2) & 0x03
    s = int(diminfo >> 4) & 0x03

    return f-1, p-1, s-1

def _diminfo_from_fps(f, p, s):
    """
    Taken from nifti1.h

    #define FPS_INTO_DIM_INFO(fd,pd,sd) ( ( ( ((char)(fd)) & 0x03)      ) |  \
    ( ( ((char)(pd)) & 0x03) << 2 ) |  \
    ( ( ((char)(sd)) & 0x03) << 4 )  )

    Because NIFTI expects values from 1-3 with 0 being 'undefined',
    we have to add 1 to each of (f,p,s).
    """
    if f not in [-1,0,1,2] or p not in [-1,0,1,2] or s not in [-1,0,1,2]:
        raise ValueError, 'f,p,s must be in [-1,0,1,2]'
    defed = filter(lambda x: x >= 0, (f,p,s))
    if len(defed) != len(set(defed)):
        raise ValueError, 'f,p,s axes must be different'
    return ((f+1) & 0x03) + (((p+1) & 0x03) << 2) + (((s+1) & 0x03) << 4)

def coordmap4io(coordmap):
    """
    Create a valid coordmap for saving with a NIFTI file.
    Also returns the NIFTI diminfo and pixdim header
    attributes.

    Inputs:
    -------

    coordmap: `CoordinateMap`

    Returns: (newcmap, transp_order, pixdim, nifti_diminfo)
    --------

    newcmap: `CoordinateMap`
           a new CoordinateMap that can be used with a (possibly
           transposed array) in a proper Image. 

    transp_order: `list`
           a list that should be used to transpose any Image
           with this coordmap to allow it to be saved as NIFTI

    pixdim: np.ndarray(dtype=np.float)
           non-negative pixdim values to be saved as NIFTI

    nifti_diminfo: int
           a valid NIFIT diminfo value, based on the order
           of i(='phase'), j(='freq'), k(='slice') in the
           input_coords of newcmap
           

    """
    # This is slightly silly because it calls coerce_coordmap 3 times...
    # but this has very small overhead

    newcmap, order = coerce_coordmap(coordmap)
    pixdim = get_pixdim(coordmap)
    diminfo = get_diminfo(coordmap)
    return newcmap, order, pixdim, diminfo
