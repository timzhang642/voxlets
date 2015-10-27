'''
Extracts all the shoeboxes from all the training images
'''
import numpy as np
import cPickle as pickle
import sys
import os
from time import time
import system_setup
import yaml
import functools
import scipy.io

sys.path.append(os.path.expanduser('~/projects/shape_sharing/src/'))
from common import scene, features

parameters_path = './training_params_nyu.yaml'
parameters = yaml.load(open(parameters_path))

if parameters['training_data'] == 'oisin_house':
    import real_data_paths as paths
elif parameters['training_data'] == 'synthetic':
    import synthetic_paths as paths
elif parameters['training_data'] == 'nyu_cad':
    import nyu_cad_paths as paths
else:
    raise Exception('Unknown training data')


def sbox_flatten(sbox):
    """Applied to the GT shoeboxes after extraction"""
    return sbox.V.flatten()


# where to log the failures
logf = open('/home/michael/Desktop/failure_log.txt', 'w')

cobwebengine = features.CobwebEngine(parameters['cobweb_offset'],
    mask=parameters['cobweb_use_mask'])
sampleengine = features.SampledFeatures(
    parameters['vox_num_rings'], parameters['vox_radius'])

def process_sequence(sequence, pca, mask_pca, voxlet_params):

    print "-> Processing " + sequence['name']

    try:
        sc = scene.Scene(parameters['mu'], voxlet_params)
        sc.load_sequence(sequence, frame_nos=0, segment_with_gt=True, voxel_normals='gt_tsdf')
    except:
        print "FAILED"
        logf.write(sequence['name'] + '\n')
        return

    # sampling locations to get the voxlets from
    # import pdb; pdb.set_trace()
    idxs = sc.sample_points(parameters['number_points_from_each_image'],
                      additional_mask=sc.gt_im_label != 0,
                      nyu=parameters['training_data'] == 'nyu_cad')

    # save these to a temp file
    scipy.io.savemat(paths.data_folder + 'tmp_idxs.mat', {'idxs':idxs})

    print "-> Extracting shoeboxes and features..."
    t1 = time()
    gt_shoeboxes = [sc.extract_single_voxlet(
        idx, extract_from=parameters['extract_from'], post_transform=sbox_flatten) for idx in idxs]
    np_sboxes = np.vstack(gt_shoeboxes)

    cobwebengine.set_image(sc.im)
    np_cobweb = np.array(cobwebengine.extract_patches(idxs))

    sampleengine.set_scene(sc)
    np_samples = sampleengine.sample_idxs(idxs)

    # Doing the mask trick...
    np_masks = np.isnan(np_sboxes).astype(np.float16)
    np_sboxes[np_masks == 1] = np.nanmax(np_sboxes)

    print "Nans: ", np.isnan(np_sboxes).sum()
    print "Nans: ", np.isnan(np_masks).sum()
    print "Nans: ", np.isnan(sc.gt_tsdf.V).sum()

    if np.isnan(np_sboxes).sum() > 0 or np.isnan(np_masks).sum() > 0:
        print "Found nans..."
        return

    # must do the pca now after doing the mask trick
    np_sboxes = pca.transform(np_sboxes)
    np_masks = mask_pca.transform(np_masks)

    print "...Shoeboxes are shape ", np_sboxes.shape
    print "Took %f s" % (time() - t1)

    savefolder = paths.voxlets_data_path % voxlet_params['name']
    if not os.path.exists(savefolder):
        os.makedirs(savefolder)

    savepath = savefolder + sequence['name'] + '.pkl'
    print "-> Saving to " + savepath

    D = dict(shoeboxes=np_sboxes, masks=np_masks, cobweb=np_cobweb, samples=np_samples, idxs=idxs)
    with open(savepath, 'w') as f:
        pickle.dump(D, f, protocol=pickle.HIGHEST_PROTOCOL)


if __name__ == '__main__':

    # Repeat for each type of voxlet in the parameters
    for voxlet_name, voxlet_params in parameters['voxlet_sizes'].iteritems():

        print "Processing voxlet type :", voxlet_name
        tic = time()

        print "-> Loading PCA models"
        pca_savefolder = paths.voxlets_dictionary_path % voxlet_name
        pca = pickle.load(open(pca_savefolder + 'voxlets_pca.pkl'))
        mask_pca = pickle.load(open(pca_savefolder + 'masks_pca.pkl'))

        print "-> Extracting the voxlets, type %s" % voxlet_name
        func = functools.partial(process_sequence,
            pca=pca, mask_pca=mask_pca, voxlet_params=voxlet_params)

        if system_setup.multicore:
            # need to import these *after* pool_helper has been defined
            import multiprocessing
            pool = multiprocessing.Pool(system_setup.cores)
            pool.map(func, paths.all_train_data)
            pool.close()
            pool.join()
        else:
            map(func, paths.all_train_data)

        print "In total took %f s" % (time() - tic)

logf.close()
