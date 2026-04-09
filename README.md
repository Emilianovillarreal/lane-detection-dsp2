# 🚗 Lane Detection System v2 - Adaptive ROI

This repository contains a lane detection system optimized for real-time computer vision, specifically designed to run on low-resource devices such as the Raspberry Pi.

---

## 🚀 Key Features

- **Dynamic and Adaptive ROI**  
  The system adjusts the Region of Interest (ROI) based on the last known position of the lane lines, optimizing CPU usage.

- **Lane Memory**  
  Implements a frame counter to maintain the trajectory even if the lane lines temporarily disappear (up to 25 frames).

- **Color Segmentation**  
  HSV filters configured to detect white and yellow lane lines under various lighting conditions.

- **Real-Time Alerts**  
  Detects states such as *"Lane Departure"* or *"Lane Crossing"*.

---

## 🛠 Installation and Usage

### 1. Clone the repository
```bash
git clone https://github.com/your-username/your-repo.git
