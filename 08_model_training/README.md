# Activity 08 - Train and Test the GooseBot AI Model

## Mission

Train a YOLO11 model on the labeled dataset, evaluate its validation results, test it on unseen images, save the best weights, and demonstrate live detection with a laptop webcam.

## Why It Matters

Training turns labeled examples into the perception function used for autonomous driving. Validation and webcam testing reveal whether the model has learned useful visual patterns rather than memorizing the training images. The resulting `best.pt` file becomes the input to RKNN conversion.

## Success Criteria

- Training uses the intended dataset version and class list.
- The run completes and produces `best.pt`.
- Validation metrics and example predictions are recorded.
- The model detects assigned objects from a live laptop webcam.
- Results and weights are copied to persistent storage before the Colab runtime ends.

## Prerequisites and Provided Files

- Complete [Activity 07](../07_dataset_creation/README.md).
- Exported dataset with a working `data.yaml`.
- Google account for Colab/Drive, or a local machine with a suitable Python environment and preferably an NVIDIA GPU.
- [GooseBot Colab notebook](GooseBot_Training_using_Google_Colab.ipynb).
- [Local trainer example](trainer.py).

Google Colab is recommended when the laptop has no suitable discrete GPU. Runtime availability and GPU type are controlled by Google and may vary.

## Part 1 - Store the Dataset in Google Drive

1. Create a `GooseBot` folder in Google Drive.
2. Upload and extract the complete dataset so `data.yaml`, `train`, `valid`, and `test` remain together.
3. Record the exact Drive path to `data.yaml`.
4. Upload [`GooseBot_Training_using_Google_Colab.ipynb`](GooseBot_Training_using_Google_Colab.ipynb) to Colab or open it from Drive.

The notebook contains example paths. You must change them to match your Drive. Do not create a second nested folder accidentally when extracting the ZIP.

## Part 2 - Select a Colab Runtime and Mount Drive

1. In Colab, select **Runtime -> Change runtime type** and choose a GPU when available.
2. Connect the runtime.
3. Mount Google Drive when the notebook requests it and approve only the access needed for your own files.
4. Install and verify Ultralytics:

   ```python
   !pip install ultralytics
   import ultralytics
   ultralytics.checks()
   ```

The installation must be repeated after Colab creates a fresh runtime.

## Part 3 - Configure Training

The core training code is:

```python
from ultralytics import YOLO

model = YOLO("yolo11n.pt")
results = model.train(
    data="/content/drive/MyDrive/GooseBot/path/to/data.yaml",
    epochs=100,
    imgsz=640,
)
```

Update only the dataset path at first. `yolo11n.pt` starts from pretrained nano-model weights. One hundred epochs and 640-pixel images are the reference settings; change them only when directed or when you can explain the tradeoff.

Before starting a long run, print or inspect `data.yaml` and confirm the class names are correct.

## Part 4 - Train and Preserve the Run

Run the training cell and note the run directory printed by Ultralytics, for example:

```text
/content/runs/detect/train/weights/best.pt
```

Repeated runs may be named `train2`, `train3`, and so on. Do not assume a fixed run number. After training:

1. locate `weights/best.pt` in the actual run directory;
2. copy the complete run directory to Google Drive;
3. confirm `best.pt` exists in Drive before disconnecting; and
4. download `best.pt` to the laptop for webcam testing and later RKNN conversion.

## Part 5 - Evaluate the Model

Run validation:

```python
metrics = model.val()
print("mAP50-95:", metrics.box.map)
print("mAP50:", metrics.box.map50)
print("mAP75:", metrics.box.map75)
```

Then predict on the test images, not the training images:

```python
model.predict(
    "/content/drive/MyDrive/GooseBot/path/to/test/images",
    save=True,
)
```

Inspect several successes and failures. A high single metric is not proof of readiness, especially for a small dataset. Check per-class behavior, missed lanes, incorrect boxes, and visually different test scenes.

## Part 6 - Test the Model on the Laptop Webcam

Create a separate local virtual environment. Windows PowerShell example:

```powershell
cd C:\goose-ai
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install ultralytics opencv-python
yolo predict model=best.pt source=0 show=True conf=0.5
```

macOS or Linux uses `source .venv/bin/activate`. Put `best.pt` in the current directory or use its full path. Press `q` in the prediction window or Ctrl+C in the terminal to stop.

Test real ducks, lane/stop examples, or instructor-approved images displayed on another device. Include both successful and difficult examples.

## Optional - Train Locally

From a Linux, macOS, or WSL terminal:

```bash
python3 -m venv trainenv
source trainenv/bin/activate
python -m pip install --upgrade pip
python -m pip install ultralytics
mkdir -p ~/yolotrain
cd ~/yolotrain
```

Copy `trainer.py` and the extracted dataset into the folder, update the `data=` path, and run:

```bash
python trainer.py
```

CPU-only training can be extremely slow. Keep training, conversion, and ROCK 5C runtime environments separate.

## Command Breakdown

| Code or option | Meaning |
|---|---|
| `YOLO("yolo11n.pt")` | loads pretrained YOLO11 nano weights as the starting point |
| `data=.../data.yaml` | selects dataset splits and class mapping |
| `epochs=100` | makes 100 passes through the training data |
| `imgsz=640` | resizes model input to 640 pixels for training/inference |
| `model.val()` | evaluates the trained run on the validation split |
| `metrics.box.map50` | mean average precision at 0.50 IoU; interpret with other metrics and examples |
| `model.predict(..., save=True)` | runs inference and writes annotated results |
| `source=0` | selects the default webcam |
| `conf=0.5` | hides detections below a 0.5 confidence threshold |

## What to Submit

Unless Canvas says otherwise, submit:

- the downloaded `.ipynb` notebook;
- a share link to the Colab notebook with the required access;
- a screenshot of the final validation metrics and several test predictions;
- a screenshot or short video of webcam detection on the laptop;
- the dataset version, training settings, and name of the saved weights; and
- each group member's contribution when this is a group activity.

Do not publish private Drive links that expose unrelated files.

## Troubleshooting

| Problem | Check |
|---|---|
| dataset path not found | inspect Drive folders and use the exact `data.yaml` path |
| labels/classes are wrong | stop training and correct `data.yaml` or dataset export before continuing |
| Colab disconnects | save checkpoints/results to Drive and rerun setup cells in a new runtime |
| result folder is not `train` | read the path printed by the current run; repeated runs receive numeric suffixes |
| webcam does not open | close other camera applications and try the correct source index |
| model performs well only on dataset images | collect more varied data, fix labels, and check split leakage |

## Next Activity

Continue in student order to [Activity 05 - Convert the Model to RKNN](../05_npu_conversion/README.md).
