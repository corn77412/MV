# 照片輪播音樂影片製作程式 - 完整架構說明

## 📋 目錄
1. [程式概述](#1-程式概述)
2. [整體架構](#2-整體架構)
3. [模組劃分](#3-模組劃分)
4. [資料流程](#4-資料流程)
5. [核心演算法](#5-核心演算法)
6. [函式詳細說明](#6-函式詳細說明)
7. [設計原則](#7-設計原則)

---

## 1. 程式概述

### 1.1 功能定位
將多張照片配合音樂與歌詞字幕，自動生成帶有模糊背景效果的音樂影片。

### 1.2 技術棧
```
輸入層：使用者互動 (input)
     ↓
處理層：圖片處理 (Pillow) + 影片合成 (MoviePy)
     ↓
輸出層：影片檔案 (MP4/H.264)
```

### 1.3 核心特性
- ✅ 支援多種圖片格式（JPG, PNG, WebP, HEIC）
- ✅ 動態模糊背景合成
- ✅ LRC 歌詞時間軸同步
- ✅ 自動照片時長分配
- ✅ 字幕描邊與自動換行

---

## 2. 整體架構

### 2.1 架構圖

```
┌─────────────────────────────────────────────────────────────┐
│                      主程式 (main)                            │
│  - 使用者輸入介面                                              │
│  - 檔案驗證                                                   │
│  - 流程控制                                                   │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────────────────┐
│              影片建構引擎 (build_video)                        │
│  [1] 音樂載入    [2] 歌詞解析    [3] 時長計算                 │
│  [4] 片段生成    [5] 影片合併    [6] 檔案輸出                 │
└────────┬────────────────────────────┬───────────────────────┘
         │                            │
         ↓                            ↓
┌────────────────────┐      ┌────────────────────────┐
│  素材處理模組       │      │  字幕處理模組           │
│  - load_images     │      │  - parse_lrc           │
│  - create_frame    │      │  - get_subtitle_at_time│
│  - 模糊背景         │      │  - draw_subtitle       │
│  - 前景縮放         │      └────────────────────────┘
└────────────────────┘
         │
         ↓
┌────────────────────────────────────────────────────────────┐
│                    底層工具函式                              │
│  - create_blurred_background  (模糊背景生成)                │
│  - resize_foreground          (照片縮放)                    │
│  - validate_output_path       (路徑驗證)                    │
└────────────────────────────────────────────────────────────┘
```

---

## 3. 模組劃分

### 3.1 模組結構

```python
照片輪播音樂影片製作程式
│
├── 【配置模組】常數定義
│   ├── VIDEO_WIDTH, VIDEO_HEIGHT      # 影片規格
│   ├── VIDEO_FPS                      # 幀率
│   ├── FONT_SIZE, FONT_COLOR          # 字幕樣式
│   └── SUPPORTED_IMAGE_FORMATS        # 支援格式
│
├── 【檔案處理模組】
│   ├── parse_lrc()                    # LRC 歌詞解析
│   ├── load_images()                  # 圖片載入與排序
│   └── validate_output_path()         # 輸出路徑驗證
│
├── 【圖片處理模組】
│   ├── create_blurred_background()    # 模糊背景生成
│   ├── resize_foreground()            # 前景照片縮放
│   └── draw_subtitle()                # 字幕繪製（含描邊）
│
├── 【影格合成模組】
│   ├── create_frame()                 # 單張照片影格合成
│   └── get_subtitle_at_time()         # 時間軸字幕查詢
│
├── 【影片建構模組】
│   └── build_video()                  # 影片建構主流程
│
└── 【主控制模組】
    └── main()                         # 程式入口與流程控制
```

---

## 4. 資料流程

### 4.1 完整資料流

```
使用者輸入
    │
    ├─→ 照片資料夾路徑
    │       │
    │       ↓
    │   load_images()  ────→  排序後的照片路徑列表
    │
    ├─→ 音樂檔路徑
    │       │
    │       ↓
    │   AudioFileClip()  ───→  音樂物件 + 音樂長度
    │
    ├─→ LRC 歌詞檔路徑
    │       │
    │       ↓
    │   parse_lrc()  ───────→  [(時間, 歌詞), ...] 列表
    │
    ├─→ 字型檔路徑
    │       │
    │       └───────────────→  字型物件 (用於字幕繪製)
    │
    └─→ 輸出路徑
            │
            ↓
        validate_output_path()  ───→  驗證並修正後的路徑
```

### 4.2 影片生成流程

```
音樂長度 ÷ 照片數量 = 每張照片顯示時長
    │
    ↓
FOR 每張照片 IN 照片列表:
    │
    ├─→ 計算時間區間 [start_time, end_time]
    │
    ├─→ 定義 make_frame(t) 函數:
    │       │
    │       ├─→ 計算絕對時間: current_time = start_time + t
    │       │
    │       ├─→ 查詢當前字幕: get_subtitle_at_time(current_time)
    │       │
    │       └─→ 生成影格: create_frame(照片, 字幕, 字型)
    │               │
    │               ├─→ 建立 1920x1080 黑色畫布
    │               │
    │               ├─→ 貼上模糊背景
    │               │       │
    │               │       └─→ create_blurred_background()
    │               │               ├─ 複製原圖
    │               │               ├─ 套用 BoxBlur(25)
    │               │               ├─ 等比放大至覆蓋畫面
    │               │               └─ 置中裁切為 1920x1080
    │               │
    │               ├─→ 貼上原始照片
    │               │       │
    │               │       └─→ resize_foreground()
    │               │               ├─ 等比縮小至適合畫面
    │               │               └─ 置中定位
    │               │
    │               └─→ 繪製字幕
    │                       │
    │                       └─→ draw_subtitle()
    │                               ├─ 自動換行處理
    │                               ├─ 繪製黑色描邊
    │                               └─ 繪製白色主文字
    │
    └─→ 建立 VideoClip(make_frame).with_fps(30)
            │
            └─→ 加入 clips 列表

合併所有片段: concatenate_videoclips(clips)
    │
    ↓
加入音樂: final_video.set_audio(audio)
    │
    ↓
輸出影片: write_videofile(output_path)
```

---

## 5. 核心演算法

### 5.1 模糊背景生成演算法

```python
演算法: create_blurred_background(image)

目標: 生成覆蓋整個 1920x1080 畫面的模糊背景

步驟:
1. 複製原始圖片 → blurred
2. 套用高斯模糊 BoxBlur(25) → blurred
3. 計算縮放比例:
   scale = max(1920/原寬, 1080/原高)  # 確保完全覆蓋
4. 縮放圖片:
   new_width = int(原寬 × scale)
   new_height = int(原高 × scale)
5. 置中裁切為 1920x1080:
   left = (new_width - 1920) / 2
   top = (new_height - 1080) / 2
   裁切區域: (left, top, left+1920, top+1080)

返回: 1920x1080 模糊背景圖
```

### 5.2 前景照片縮放演算法

```python
演算法: resize_foreground(image)

目標: 將照片等比縮放至完整顯示於畫面內（不裁切）

步驟:
1. 計算縮放比例:
   scale = min(1920/原寬, 1080/原高)  # 確保完整顯示
2. 縮放圖片:
   new_width = int(原寬 × scale)
   new_height = int(原高 × scale)
3. 返回縮放後的圖片（後續由 create_frame 置中）

返回: 縮放後的照片
```

### 5.3 字幕時間軸查詢演算法

```python
演算法: get_subtitle_at_time(t, lyrics, audio_duration)

目標: 查詢時間 t 應該顯示的字幕

步驟:
1. 初始化: current_lyric = ""
2. FOR (時間點, 歌詞) IN lyrics:
   IF t >= 時間點 AND 時間點 <= 音樂總長:
      current_lyric = 歌詞
   ELSE IF t < 時間點:
      BREAK  # 已超過當前時間，停止查詢
3. 返回 current_lyric

邏輯說明:
- 歌詞按時間排序
- 每句歌詞從自己的時間點顯示到下一句開始前
- 最後一句歌詞顯示到音樂結束
```

### 5.4 字幕繪製演算法（含描邊）

```python
演算法: draw_subtitle(canvas, text, font_path)

目標: 在畫布上繪製帶黑色描邊的白色字幕

步驟:
1. 如果 text 為空，直接返回原畫布
2. 載入字型 (size=40)
3. 自動換行處理:
   FOR char IN text:
      IF 當前行長度 < 30:
         加入當前行
      ELSE:
         儲存當前行，開始新行
4. 計算字幕總高度與起始 Y 座標:
   total_height = 行數 × (40 + 10)
   start_y = 1080 × 4/5 - total_height/2
5. FOR 每一行:
   a. 計算行寬，置中對齊:
      x = (1920 - 行寬) / 2
   b. 繪製黑色描邊（9 個偏移位置）:
      FOR offset_x IN [-3, -2, -1, 0, 1, 2, 3]:
        FOR offset_y IN [-3, -2, -1, 0, 1, 2, 3]:
          IF 非中心點:
            繪製黑色文字於 (x+offset_x, y+offset_y)
   c. 繪製白色主文字於 (x, y)

返回: 繪製後的畫布
```

### 5.5 LRC 解析演算法

```python
演算法: parse_lrc(lrc_path)

目標: 解析 LRC 格式歌詞檔為時間-歌詞對列表

正則表達式: \[(\d+):(\d+)\.(\d+)\](.*)$
匹配範例: [00:12.50]這是一句歌詞

步驟:
1. 初始化空列表 lyrics = []
2. 逐行讀取檔案:
   FOR line IN file:
      IF line 匹配 LRC 格式:
         a. 提取: 分(minutes), 秒(seconds), 百分秒(centiseconds), 歌詞(text)
         b. 轉換時間: total_seconds = 分×60 + 秒 + 百分秒/100
         c. 加入列表: lyrics.append((total_seconds, text))
3. 依時間排序: lyrics.sort(key=lambda x: x[0])

返回: [(0.0, "第一句"), (5.5, "第二句"), ...]
```

---

## 6. 函式詳細說明

### 6.1 函式分類與職責

| 類別 | 函式名稱 | 輸入 | 輸出 | 職責 |
|------|---------|------|------|------|
| **檔案處理** | `parse_lrc()` | LRC 檔案路徑 | 時間-歌詞列表 | 解析歌詞時間軸 |
| | `load_images()` | 資料夾路徑 | 照片路徑列表 | 載入並排序照片 |
| | `validate_output_path()` | 輸出路徑字串 | 修正後路徑 | 驗證並修正輸出路徑 |
| **圖片處理** | `create_blurred_background()` | PIL Image | 1920×1080 模糊圖 | 生成模糊背景 |
| | `resize_foreground()` | PIL Image | 縮放後 PIL Image | 等比縮放照片 |
| | `draw_subtitle()` | 畫布+文字+字型 | 繪製後畫布 | 繪製字幕（含描邊）|
| **影格合成** | `create_frame()` | 照片路徑+字幕+字型 | NumPy 陣列 (RGB) | 合成完整影格 |
| | `get_subtitle_at_time()` | 時間+歌詞列表 | 當前字幕字串 | 時間軸查詢字幕 |
| **影片建構** | `build_video()` | 所有素材路徑 | 無(輸出檔案) | 影片建構主流程 |
| **主控制** | `main()` | 無 | 無 | 程式入口與流程控制 |

### 6.2 函式呼叫關係圖

```
main()
  │
  ├─→ load_images()
  │
  ├─→ validate_output_path()
  │
  └─→ build_video()
        │
        ├─→ AudioFileClip()  (moviepy)
        │
        ├─→ parse_lrc()
        │
        └─→ FOR 每張照片:
              │
              ├─→ make_frame(t)  [閉包函數]
              │     │
              │     ├─→ get_subtitle_at_time()
              │     │
              │     └─→ create_frame()
              │           │
              │           ├─→ Image.open()
              │           │
              │           ├─→ create_blurred_background()
              │           │     └─→ ImageFilter.BoxBlur()
              │           │
              │           ├─→ resize_foreground()
              │           │     └─→ Image.resize()
              │           │
              │           └─→ draw_subtitle()
              │                 └─→ ImageDraw.text()
              │
              └─→ VideoClip(make_frame).with_fps()
```

---

## 7. 設計原則

### 7.1 模組化設計

**單一職責原則 (SRP)**
- 每個函式只負責一個明確的任務
- 例如：`create_blurred_background()` 只負責背景模糊，不處理字幕

**高內聚低耦合**
```python
# ✅ 好的設計：函式獨立可測試
def create_blurred_background(image):
    # 輸入：PIL Image
    # 輸出：PIL Image
    # 無外部依賴
    pass

# ❌ 避免：函式依賴全域變數
def create_blurred_background():
    global current_image  # 不好的設計
    pass
```

### 7.2 資料流設計

**管道式處理 (Pipeline Pattern)**
```python
原始照片
  → create_blurred_background()  # 背景層
  → resize_foreground()          # 前景層
  → draw_subtitle()              # 字幕層
  → 最終影格
```

**閉包應用 (Closure Pattern)**
```python
def make_frame(t, img_path=image_path, start_t=start_time):
    # 捕獲外部變數：img_path, start_time, lyrics, font_path
    current_time = start_t + t
    subtitle = get_subtitle_at_time(current_time, lyrics, audio_duration)
    return create_frame(img_path, subtitle, font_path)

# 優點：每個 VideoClip 擁有獨立的上下文
```

### 7.3 錯誤處理策略

**輸入驗證層次**
```
Layer 1: 主程式層 (main)
  → 檔案存在性檢查
  → 格式正確性檢查

Layer 2: 函式層
  → 參數有效性檢查
  → 邊界條件處理

Layer 3: 異常捕獲層
  → try-except 包裹關鍵操作
  → 提供友善錯誤訊息
```

**早期返回原則 (Early Return)**
```python
def draw_subtitle(canvas, text, font_path):
    if not text:  # 早期返回，避免不必要的計算
        return canvas
    # 後續處理...
```

### 7.4 效能優化

**影像處理優化**
```python
# 使用高品質但高效的演算法
Image.Resampling.LANCZOS  # 縮放時使用 Lanczos 濾波器

# 避免重複計算
duration_per_image = audio_duration / num_images  # 只計算一次
```

**記憶體管理**
```python
# 及時釋放資源
audio.close()
final_video.close()
```

### 7.5 可擴展性設計

**常數配置化**
```python
# 所有魔術數字提取為常數
VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
FONT_SIZE = 40
BLUR_RADIUS = 25

# 優點：易於調整，集中管理
```

**格式支援動態化**
```python
# 根據環境動態調整支援格式
if HEIC_SUPPORTED:
    SUPPORTED_IMAGE_FORMATS = ('.jpg', '.jpeg', '.png', '.webp', '.heic', '.heif')
else:
    SUPPORTED_IMAGE_FORMATS = ('.jpg', '.jpeg', '.png', '.webp')
```

**版本相容處理**
```python
# 兼容不同版本的 API
if hasattr(clip, 'with_fps'):
    clip = clip.with_fps(VIDEO_FPS)  # 新版
else:
    clip = clip.set_fps(VIDEO_FPS)   # 舊版
```

---

## 8. 資料結構

### 8.1 核心資料結構

```python
# 歌詞資料結構
Lyrics: List[Tuple[float, str]]
# 範例: [(0.0, "第一句"), (5.5, "第二句"), (10.0, "第三句")]

# 照片列表
ImageFiles: List[str]
# 範例: ["D:\\photos\\img001.jpg", "D:\\photos\\img002.jpg"]

# 影片片段列表
Clips: List[VideoClip]
# 範例: [VideoClip(0-3s), VideoClip(3-6s), VideoClip(6-9s)]
```

### 8.2 時間軸對應關係

```
音樂時間軸:  |-------- 30 秒 --------|
            0s         15s          30s

照片時間軸:  |--Photo1--|--Photo2--|
            0-15s      15-30s

歌詞時間軸:  [0.0]歌詞1  [5.5]歌詞2  [15.0]歌詞3  [25.0]歌詞4
            ↓           ↓           ↓           ↓
            顯示至5.5s   顯示至15s    顯示至25s    顯示至30s
```

---

## 9. 程式執行流程時序圖

```
使用者    主程式       檔案處理     圖片處理     影片合成     FFmpeg
  │         │             │           │           │           │
  │ 啟動    │             │           │           │           │
  ├────────>│             │           │           │           │
  │         │ 顯示提示    │           │           │           │
  │<────────┤             │           │           │           │
  │ 輸入路徑│             │           │           │           │
  ├────────>│             │           │           │           │
  │         │ 驗證檔案    │           │           │           │
  │         ├────────────>│           │           │           │
  │         │<────────────┤           │           │           │
  │         │   載入圖片  │           │           │           │
  │         ├────────────>│           │           │           │
  │         │   返回列表  │           │           │           │
  │         │<────────────┤           │           │           │
  │         │             │           │           │           │
  │         │ 建構影片    │           │           │           │
  │         ├─────────────────────────────────────>│           │
  │         │             │  FOR 每張照片          │           │
  │         │             │           │  生成影格  │           │
  │         │             │           │<───────────┤           │
  │         │             │  模糊背景 │            │           │
  │         │             │<──────────┤            │           │
  │         │             │  縮放前景 │            │           │
  │         │             │<──────────┤            │           │
  │         │             │  繪製字幕 │            │           │
  │         │             │<──────────┤            │           │
  │         │             │  返回影格 │            │           │
  │         │             │───────────>│            │           │
  │         │             │           │  合併片段  │           │
  │         │             │           │  加入音樂  │           │
  │         │             │           │  寫入檔案  │           │
  │         │             │           │            ├──────────>│
  │         │             │           │            │   編碼    │
  │         │             │           │            │<──────────┤
  │         │<────────────────────────────────────┤            │
  │ 完成    │             │           │           │            │
  │<────────┤             │           │           │            │
```

---

## 10. 總結

### 10.1 程式特點

✅ **模組化設計**：每個函式職責單一，易於測試與維護  
✅ **資料流清晰**：從輸入到輸出，流程一目了然  
✅ **錯誤處理完善**：多層驗證，友善錯誤提示  
✅ **效能優化**：避免重複計算，及時釋放資源  
✅ **可擴展性強**：支援格式動態調整，版本相容處理  

### 10.2 架構優勢

1. **分層架構**：輸入驗證 → 資料處理 → 影格合成 → 影片輸出
2. **函式式風格**：純函數設計，無副作用，易於測試
3. **管道式處理**：圖片處理如同流水線，每一步獨立可測
4. **閉包應用**：利用閉包特性，為每個影片片段建立獨立上下文

### 10.3 未來擴展方向

```python
# 可擴展功能示意
def add_transition_effects():
    """加入轉場效果（淡入淡出、滑動等）"""
    pass

def add_custom_filters():
    """支援自訂濾鏡（黑白、復古、HDR等）"""
    pass

def add_text_animations():
    """字幕動畫效果（打字機、飛入等）"""
    pass

def batch_processing():
    """批次處理多個影片專案"""
    pass

def gui_interface():
    """圖形化使用者介面"""
    pass
```

---

## 11. 快速參考

### 11.1 程式架構總覽

```
程式 = 輸入層 + 處理層 + 輸出層

輸入層:
  - 使用者互動 (main)
  - 檔案驗證 (validate_*)

處理層:
  - 檔案解析 (parse_lrc, load_images)
  - 圖片處理 (create_blurred_background, resize_foreground)
  - 字幕處理 (draw_subtitle, get_subtitle_at_time)
  - 影格合成 (create_frame)

輸出層:
  - 影片建構 (build_video)
  - 檔案輸出 (write_videofile)
```

### 11.2 關鍵技術

- **圖片處理**：Pillow (PIL Fork)
- **影片合成**：MoviePy
- **影片編碼**：FFmpeg (MoviePy 底層)
- **時間軸同步**：LRC 時間戳對應
- **記憶體優化**：動態生成影格，避免全部載入記憶體

---
