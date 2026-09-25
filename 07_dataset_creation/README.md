# Activity 07 - Create and Label a GooseBot Dataset

## Mission

Create a Roboflow object-detection project, label images with bounding boxes, inspect label quality, and export a YOLO dataset that can train a model for GooseBot perception.

## Why It Matters

The model can learn only from the examples and labels it receives. Inconsistent boxes, missing objects, wrong class names, and data leakage often matter more than the training command. Lane following is especially sensitive because the controller uses the detected white and yellow lane positions to decide how to steer.

## Success Criteria

- Images are uploaded to an object-detection project.
- Every assigned object is labeled with a bounding box, not a segmentation polygon.
- Class names are spelled and capitalized consistently.
- Train, validation, and test splits are created without near-duplicate leakage when possible.
- The exported dataset includes images, label text files, and `data.yaml`.

## Prerequisites

- Complete [Activity 04](../04_motor_test/README.md).
- A Roboflow account and an instructor-approved project workspace.
- Either the instructor-provided introductory images or the reference images in [`train/images.zip`](goosedataset_final/goosedataset_final/train/images.zip).

Do not upload images containing faces, student records, network credentials, or other private information.

## Part 1 - Understand the Two Dataset Tasks

The course may use one or both of these stages:

1. **Duck-detection practice:** label `duck` in a small image set, train a first model, and verify the complete workflow.
2. **Full GooseBot perception:** label road and obstacle classes used by the autonomous robot.

The reference dataset in this repository uses eight classes:

```text
duck
l_intersection
mouse
redline
stopsign
t_intersection
whiteline
yellowline
```

The current class list is also recorded in [`data.yaml`](goosedataset_final/goosedataset_final/data.yaml). Your assigned dataset may contain a subset or an instructor-approved revision.

## Part 2 - Create the Roboflow Project

1. Sign in at [Roboflow](https://roboflow.com/).
2. Create or fork the instructor-specified project.
3. Select **Object Detection** as the project type.
4. Upload the assigned images.
5. Confirm that image orientation and resolution look correct before labeling.

The full reference dataset is available through its [Roboflow Universe page](https://universe.roboflow.com/lznfjv/goosesupreme-gzu7t/dataset/2). If the instructor provides a different project/version, use that assigned version.

## Part 3 - Label with Bounding Boxes

For each image:

1. Draw a tight rectangular box around every assigned object that is sufficiently visible.
2. Select the exact class name. Do not create variants such as `Duck`, `ducks`, or `yellow_line` unless the class specification uses them.
3. Label partially occluded objects consistently.
4. For lane markings, box the visible region the instructor intends the model to localize; use the same policy in every image.
5. Mark an image complete only after scanning the whole frame for missed objects.

Use bounding boxes, not segmentation, for this workflow. A box that includes large amounts of unrelated background weakens localization.

## Part 4 - Perform Label Quality Control

Review the dataset as a group before generating a version:

- filter by class and compare box tightness;
- inspect images with zero labels;
- correct misspelled or duplicate classes;
- check small and partially occluded objects;
- ensure road images contain variety in camera angle and lighting; and
- keep nearly identical video frames in the same split to reduce data leakage.

Each group member should review images labeled by someone else.

## Part 5 - Generate and Export a Version

1. Create train, validation, and test splits.
2. Use resizing compatible with the later training image size, normally 640 x 640.
3. Apply augmentation only to the training split and keep transformations physically plausible.
4. Generate a version and record its version number and preprocessing settings.
5. Export in the YOLO format requested by the current Ultralytics workflow.
6. Download the ZIP or use the generated notebook code snippet.
7. Extract the dataset and confirm this general structure:

   ```text
   dataset/
   |-- data.yaml
   |-- train/
   |   |-- images/
   |   `-- labels/
   |-- valid/
   |   |-- images/
   |   `-- labels/
   `-- test/
       |-- images/
       `-- labels/
   ```

Open `data.yaml` and confirm its paths and class names match the extracted directories.

## Command Breakdown

Roboflow performs most of this activity in the browser. These optional terminal commands help inspect an extracted dataset on macOS, Linux, or WSL:

```bash
find dataset/train/images -type f | wc -l
find dataset/train/labels -type f | wc -l
sed -n '1,40p' dataset/data.yaml
```

| Command | Meaning |
|---|---|
| `find ... -type f` | lists regular files below a directory |
| `wc -l` | counts the listed files |
| `sed -n '1,40p'` | prints the first 40 lines without editing the YAML file |
| `data.yaml` | tells YOLO where the splits are and maps numeric label IDs to class names |

Image and label counts may differ if intentionally negative images contain no objects, but investigate every unexpected mismatch.

## What to Submit

Unless Canvas says otherwise, submit:

- a link to the assigned Roboflow project/version, with instructor access if the project is private;
- one screenshot showing labeled examples and the class list;
- the exported `data.yaml`;
- a short label-quality summary describing at least two corrections made during review; and
- each group member's contribution.

Do not submit account passwords or unrelated/private images.

## Troubleshooting

| Problem | Check |
|---|---|
| duplicate class names | merge or relabel them before generating the dataset version |
| labels appear on the wrong images | verify the export format and that image/label base filenames match |
| `data.yaml` paths fail later | paths are relative to the YAML location; preserve the exported directory structure |
| validation score looks unrealistically high | look for duplicated or near-duplicated frames across splits |
| lane boxes are inconsistent | define one lane-labeling rule, review examples together, and relabel outliers |

## Next Activity

Continue to [Activity 08 - Train and Test the AI Model](../08_model_training/README.md).
