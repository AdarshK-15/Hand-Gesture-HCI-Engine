\# Real-Time Multimodal Hand Gesture \& Air-Canvas HCI Engine



A touchless Human-Computer Interface (HCI) running on a live webcam feed that detects 21 skeletal hand landmarks in 3D space and maps dynamic finger postures into desktop actions.



\## Features

\- \*\*Virtual Mouse Navigation:\*\* Exponential Moving Average (EMA) smoothing for jitter-free cursor tracking.

\- \*\*Native Clicking:\*\* Debounced left-click trigger using index-middle fingertip proximity.

\- \*\*Continuous 2D Scrolling:\*\* Intuitive document and webpage scrolling via two-finger vertical displacement.

\- \*\*Air-Canvas Drawing:\*\* Persistent mid-air drawing layer with real-time bitwise masking and fist-based canvas reset.

\- \*\*Master Volume Modulation:\*\* Euclidean distance mapping directly interfacing with Windows native Core Audio endpoints (`IAudioEndpointVolume`).



\## Tech Stack

\- \*\*Languages \& Frameworks:\*\* Python 3.13, OpenCV, MediaPipe Tasks Vision API, NumPy

\- \*\*OS Hardware Interfacing:\*\* PyCaw (Windows COM APIs), PyAutoGUI

