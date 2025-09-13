# Cut Pro - Mini Tool 🎬

**Licensed Professional Video Editing Tool** - Complete with server-based license protection, perfect centering, auto folders, and custom naming.

## 🔐 **License System**
- **Server-based validation** - Secure license activation required
- **One license per PC** - MAC address binding prevents sharing
- **Remembered license keys** - Enter once, activate each session
- **Auto-closing success dialogs** - Professional user experience

## 🚀 **Quick Start**
```bash
pip install -r requirements.txt
python auto.py
```
**⚠️ Note**: Internet connection required for license activation

## ✨ **Mini Tool Interface** (700×550 - Centered on Screen)

```
┌─────────────────────────────────────────────────────────────┐
│ Cut Pro - Mini Tool  License Not Activated [License Key] [Activate] │
├─────────────────────┬───────────────────────┬───────────────┤
│   📁 IMPORT VIDEOS  │    🛠️ VIDEO TOOLS    │ 📋 File List │
│      (300px)        │      (400px)         │   (Dynamic)   │
│                     │                      │               │
│ [Import Files]      │ [🔄 Rotate Video]    │ 1. video1.mp4 │
│ [Import Folder]     │                      │    1920x1080  │
│                     │ [📐 Crop Video]      │               │
│ 📋 Video Files      │                      │ 2. video2.mp4 │
│ (5 Videos):         │ [🔀 Merge Videos]    │    720x1280   │
│ ┌─────────────────┐ │                      │               │
│ │ 1. video1.mp4   │ │ [⚡ Change Speed]    │ [Remove] btns │
│ │    1920x1080 [×]│ │                      │               │
│ │ 2. video2.mp4   │ │ [🎵 Extract Audio]   │               │
│ │    720x1280  [×]│ │                      │               │
│ │ 3. video3.mp4   │ │ [✨ Quality Enhancer]│               │
│ │    1080x1920 [×]│ │                      │               │
│ └─────────────────┘ │ [🌊 Blur Background] │               │
│                     │                      │               │
│ 📝 Custom Name:     │                      │               │
│ [my_project] [Rename] │                    │               │
│                     │                      │               │
│ 💾 Output Folder:   │                      │               │
│ [_______] [Browse]  │                      │               │
│                     │                      │               │
│ [Clear All]         │                      │               │
├─────────────────────┴───────────────────────┴───────────────┤
│ Ready                                       │ Progress Bar  │
└─────────────────────────────────────────────────────────────┘
```

## 🎯 **NEW FEATURES**:

### **🔐 Professional License System**:
- **Server validation** - License verified with secure server
- **One PC per license** - MAC address binding prevents piracy
- **Remembered activation** - Enter license once, click activate each session
- **Feature protection** - ALL functions disabled until license activated
- **Auto-close dialogs** - Success messages disappear after 5 seconds

### **📋 Video File Management**:
- **Live file list** - See imported videos with resolution info
- **Individual removal** - Remove specific videos with × buttons  
- **Smart file counting** - "Video Files (5 Videos)" dynamic header
- **Video info display** - Shows resolution for each imported file

### **✨ Quality Enhancement**:
- **AI Upscaling** - Enhance videos to 1080p, 2K, or 4K resolution
- **Aspect ratio preservation** - Maintains original video proportions
- **Auto quality** - Smart enhancement based on source resolution

### **🌊 Blur Background Conversion**:
- **9:16 to 16:9 conversion** - Transform vertical videos to landscape
- **Multiple blur styles** - Gaussian, Box, and Motion blur options
- **Professional output** - Perfect for YouTube, Facebook, TV displays

### **📝 Custom File Naming**:
- **Optional custom name** - leave blank to use original names
- **Smart numbering** - multiple videos get "name_01", "name_02", etc.
- **Merge naming** - "myproject_merged_all.mp4" or "myproject_pair_01.mp4"
- **Works with all tools** - rotate, crop, merge, speed, audio

### **🎯 Perfect Centering**:
- **Main window** - opens centered on screen
- **All dialogs** - custom dialogs that follow main window
- **Move main window** - dialogs automatically re-center ✅
- **Professional behavior** - like commercial software

### **📁 Smart Folder Management**:
- **Import videos** → Auto creates "Output" folder in same location
- **After processing** → Auto moves original videos to "Used" folder
- **Clean organization** → Original videos safely stored, processed videos in Output
- **Example**: `D:/MyVideo/Short-1/8/Output/` (processed) + `D:/MyVideo/Short-1/8/Used/` (originals)

## 🛠️ **How Custom Naming Works**:

### **📝 Single Video**:
```
Custom name: "my_video"
Result: my_video_rot90.mp4, my_video_crop_16x9.mp4, etc.
```

### **📝 Multiple Videos**:
```
Custom name: "project" + 5 videos
Results: project_01_rot90.mp4, project_02_rot90.mp4, project_03_rot90.mp4, etc.
```

### **📝 Merge Operations**:
```
Custom name: "Fish bait"
Merge All: Fish bait_merged_all.mp4
Merge Pairs: Fish bait_01.mp4, Fish bait_02.mp4, Fish bait_03.mp4
```

## ✅ **Complete Workflow**:

### **1. 📁 Import**:
- **Import Files/Folder** → Videos loaded + Auto creates "Output" folder

### **2. 📝 Custom Name** (Optional):
- **Enter custom name** → "Fish bait", "my_project", etc.
- **Leave blank** → Uses original video names

### **3. 🛠️ Choose Tool**:
- **Click tool** → Dialog opens **centered on main window**
- **Move main window** → Dialog **follows automatically** ✅

### **4. ✅ Process**:
- **Select option** → Processing starts with custom names
- **Results saved** → Check "Output" folder
- **Original videos moved** → Automatically moved to "Used" folder

### **5. 🗂️ Final Organization**:
- **Output/** → Fish bait_01.mp4, Fish bait_02.mp4 (processed videos)
- **Used/** → 1.mp4, 1_2.mp4, 2.mp4 (original videos safely stored)

## 🎯 **Your Features - All Working**:

### **🔄 Rotate Video** → Popup with:
- 90° (16:9→9:16) - Landscape to Portrait
- 180° (Upside Down) - Full rotation
- 270° (9:16→16:9) - Portrait to Landscape
- Flip Horizontal - Mirror effect

### **📐 Crop Video** → Popup with:
- 16:9 (YouTube) - Widescreen format
- 9:16 (TikTok) - Vertical format
- 1:1 (Instagram) - Square format
- 4:3 (Standard) - Traditional format

### **🔀 Merge Videos** → Popup with:
- **Merge All → 1** - Combine all videos
- **Merge Pairs (2→1)** - Your exact request!

### **⚡ Change Speed** → Popup with:
- 0.5x (Slow Motion), 1.5x (Fast), 2x (Double), 3x (Very Fast)

### **🎵 Extract Audio** → Popup with:
- Extract MP3, Extract WAV

### **✨ Quality Enhancer** → Popup with:
- Enhance to 1080p (Full HD) - Perfect for most displays
- Enhance to 2K (1440p) - High definition quality  
- Enhance to 4K (2160p) - Ultra high definition
- Auto Enhance (Best Quality) - Smart optimization

### **🌊 Blur Background** → Popup with:
- Gaussian Blur (Soft & Natural) - Smooth background effect
- Box Blur (Uniform Effect) - Even blur distribution
- Motion Blur (Dynamic) - Horizontal motion effect
- Zoom Blur (Radial) - Intense blur for dramatic effect

## 📊 **Merge Examples with Custom Names**:

### **Merge All**:
```
Custom name: "vacation"
[video1.mp4, video2.mp4, video3.mp4] → [vacation_merged_all.mp4]
```

### **Merge Pairs (2→1)**:
```
Custom name: "Fish bait"  
[vid1, vid2, vid3, vid4, vid5, vid6] → [Fish bait_01.mp4, Fish bait_02.mp4, Fish bait_03.mp4]

Your example: 100 videos → 50 videos with clean organized names ✅
```

## 🗂️ **Perfect File Organization**:

### **📁 Your Folder Structure After Processing**:
```
D:/MyVideo/Short-1/8/
├── Output/                    # Processed videos
│   ├── Fish bait_01.mp4      # Merged pair 1
│   ├── Fish bait_02.mp4      # Merged pair 2  
│   ├── Fish bait_03.mp4      # Merged pair 3
│   └── ...
├── Used/                      # Original videos (moved automatically)
│   ├── 1.mp4                 # Original video 1
│   ├── 1_2.mp4               # Original video 2
│   ├── 2.mp4                 # Original video 3
│   └── ...
└── [Other files untouched]
```

### **✅ Benefits**:
- **Clean separation** - processed vs original videos
- **Original videos safe** - moved to "Used" folder, not deleted
- **Easy to find** - processed videos in "Output" folder
- **Organized naming** - your custom name + sequential numbers

## 🏆 **Ultimate Mini Tool**:

**Cut Pro Mini** is now the ultimate professional video editing tool:
- ✅ **License protection** - Server-based validation, one PC per license
- ✅ **Complete video toolkit** - rotate, crop, merge, speed, audio, quality, blur
- ✅ **Quality enhancement** - AI upscaling to 1080p, 2K, 4K resolutions
- ✅ **Blur background conversion** - 9:16 to 16:9 with professional effects
- ✅ **Live video management** - Dynamic file list with individual removal
- ✅ **Custom file naming** - clean "Fish bait_01.mp4" format
- ✅ **Auto folder management** - Output + Used folders created automatically
- ✅ **Perfect centering** - all dialogs follow main window movement
- ✅ **Smart organization** - original videos safely moved to Used folder
- ✅ **Professional workflow** - commercial-quality file management

## 🛠️ **System Requirements**:
- **Python 3.7+** - Modern Python version required
- **FFmpeg** - For video processing (must be in PATH)
- **Internet connection** - Required for license activation
- **Windows/macOS/Linux** - Cross-platform compatibility

## 🔧 **Building Executable**:
```bash
# Run the automated build script
setup.bat    # Windows
# Creates CutPro.exe in dist/ folder
```

## 📄 **License Information**:
- **Product ID**: `cutpro-mini`
- **License Server**: `https://license-server-pro.vercel.app/`
- **Machine Binding**: MAC address based (one PC per license)
- **Activation**: Required each session, but license key remembered

**Licensed, professional, intelligent, and perfectly positioned!** 🎬✨🔐

---

**Ready**: `python auto.py` → Activate License → Start Editing! 🚀