% script to propose 3D basis shapes for a specific region, and to somehow
% visualise. No transformations or anything clever like that yet...

% a script to load in a depth image, convert to xyz, compute normals and segment
clear
cd ~/projects/shape_sharing/3D/src/
addpath plotting/
addpath features/
addpath ./file_io/matpcl/
addpath(genpath('../../common/'))
addpath transformations/
addpath utils/
addpath ../../2D/src/segment/
addpath ../../2D/src/utils
run ../define_params_3d.m
load(paths.structured_model_file, 'model')

%% loading in some of the ECCV dataset
clear cloud
filepath = '/Users/Michael/data/others_data/ECCV_dataset/pcd_files/frame_20111220T111153.549117.pcd';
P = loadpcd(filepath);
cloud.xyz = P(:, :, 1:3);
cloud.xyz = reshape(permute(cloud.xyz, [3, 1, 2]), 3, [])';
cloud.rgb = P(:, :, 4:6);
cloud.depth = reshape(P(:, :, 3), [480, 640]);
[cloud.normals, cloud.curvature] = normals_wrapper(cloud.xyz, 'knn', 50);

%% running segment soup algorithm
[idxs, idxs_without_nans, probabilities, all_idx] = segment_soup_3d(cloud, params.segment_soup);

%% plotting segments
%close all
plot_segment_soup_3d(cloud.rgb.^0.2, idxs);
for ii = 1:length(probabilities)
    subplot(2, 4, ii)
    title(num2str(probabilities(ii)))
end
set(findall(gcf,'type','text'),'fontSize',18,'fontWeight','bold')

%% Choosing a segment and computing the feature vector
segment.seg_index = 4;
segment.idx = idxs(:, segment.seg_index);
segment.mask = reshape(segment.idx, [480, 640]) > 0.1;
segment.xyz = cloud.xyz(segment.idx>0.5, :);
segment.norms = cloud.normals(segment.idx>0.5, :);
segment.scaled_xyz = segment.xyz * normalise_scale(segment.xyz);
segment.shape_dist = shape_distribution_norms_3d(segment.scaled_xyz, segment.norms, params.shape_dist);
segment.edge_shape_dist = edge_shape_dists_norms(segment.mask, params.shape_dist.edge_dict);

% Find closest match and load image etc...
%dists = chi_square_statistics_fast(segment.shape_dist, model.all_shape_dists);
dists = chi_square_statistics_fast(segment.edge_shape_dist, model.all_edge_shape_dists);
[~, idx] = sort(dists, 'ascend');
 
% plotting the closest matches
num_to_plot = 20;
[p, q] = best_subplot_dims(num_to_plot);

subplot(p, q, 1)
imagesc(boxcrop_2d(segment.mask))
axis image

for ii = 1:(num_to_plot-1)
    
    this.model_idx = model.all_model_idx(idx(ii));
    this.model = params.model_filelist{this.model_idx};
    this.view = model.all_view_idx(idx(ii));
    this.path = sprintf(paths.basis_models.rendered, this.model, this.view);
    load(this.path, 'depth')
    max_depth = max(depth(:));
    depth(abs(depth-max_depth)<0.01) = nan;
    
    subplot(p, q, ii+1)
    imagesc(depth)
    title([num2str(this.model_idx) ' - ' num2str(this.view)])
    axis image off
    colormap(flipud(gray))    
end

%% idea now is to rotate each image to the best alignment.

[XY, norms] = edge_normals(segment.mask, 15);


for ii = 1:(num_to_plot-1)
    
    this.model_idx = model.all_model_idx(idx(ii));
    this.model = params.model_filelist{this.model_idx};
    this.view = model.all_view_idx(idx(ii));
    this.path = sprintf(paths.basis_models.rendered, this.model, this.view);
    load(this.path, 'depth')
    max_depth = max(depth(:));
    depth(abs(depth-max_depth)<0.01) = nan;
    
    subplot(p, q, ii+1)
    imagesc(depth)
    title([num2str(this.model_idx) ' - ' num2str(this.view)])
    axis image off
    colormap(flipud(gray))    
end


%% 
clf
iii = 1
plot(model.all_shape_dists(idx(iii), :));
hold on
plot(segment.shape_dist,'r')
hold off



