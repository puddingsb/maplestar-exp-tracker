# MapleStar EXP Tracker

MapleStar EXP Tracker 是一個給 MapleStory Worlds / MapleStar 使用的非官方桌面小工具。它會擷取遊戲視窗中的 EXP 區域，透過 PP-OCRv5 + PaddleOCR 辨識目前經驗值與百分比，並估算近期效率、5 分鐘 / 10 分鐘 / 30 分鐘預估經驗，以及升級所需時間。

這個工具只讀取畫面，不抓封包、不注入遊戲、不修改遊戲資料。

## 功能特色

- 即時辨識目前 EXP 與 EXP 百分比。
- 可手動框選 EXP 區域，支援不同視窗位置與解析度。
- 支援校正目前 EXP，避免 OCR 初始讀值偏掉。
- 支援校正目前等級，依照 MapleStar 經驗表估算升級進度。
- 顯示本次累積 EXP、近 5 分鐘速率、5 / 10 / 30 分鐘預估。
- 顯示預估升級時間。
- 針對常見 OCR 誤判加入保護：
  - `6` / `8` / `9` 混淆修正。
  - 升級後 EXP 歸零確認。
  - 避免一筆錯誤 OCR 造成連續誤判升級。
  - 上一筆低讀時，下一筆恢復正常可回補修正，避免效率爆衝。
  - 當校正等級與 EXP / 百分比不一致時，保留手動校正等級，不會只靠單筆 OCR 自動跳等。
- 可縮小成精簡視窗，方便邊玩邊看效率。
- Windows 可打包成單一 `.exe`。

## 系統需求

### 使用打包好的 Windows EXE

- Windows 10 / Windows 11
- 建議使用 64 位元系統
- 第一次啟動 PP-OCRv5 可能需要等待較久

### 從原始碼執行

- Python 3.13
- Windows 建議使用 PowerShell
- 需要可正常安裝 `requirements.txt` 內的套件

## 快速開始：使用 EXE

1. 下載或取得 `MapleStar-EXP-Tracker.exe`。
2. 啟動 MapleStory Worlds / MapleStar，並進入能看到 HP / MP / EXP 條的畫面。
3. 啟動 `MapleStar-EXP-Tracker.exe`。
4. 在「擷取來源」選擇遊戲視窗。
5. 按「框選 EXP 區域」。
6. 用滑鼠框住 EXP 數字與百分比附近。
7. 按「校正目前 EXP」，輸入遊戲畫面上正確的目前 EXP。
8. 按「校正等級」，輸入目前角色等級。
9. 按「開始追蹤」。

如果 EXP 數字會往左變長，框選時可以往左多留一點空間；不一定要框整條 EXP 條，但至少要讓數字和百分比穩定出現在框選範圍內。

## 建議框選方式

建議框選遊戲底部 EXP 數字，例如：

```text
EXP. 9924083[31.97%]
```

框選範圍建議包含：

- EXP 數字
- 百分比
- 數字左側一點預留空間，避免經驗值位數增加後超出範圍

不建議框太大，因為 HP / MP、角色名稱、聊天室文字或其他 UI 進入範圍時，會增加 OCR 誤判機率。

## 校正說明

### 校正目前 EXP

當 OCR 初始讀值不穩定，或你發現目前 EXP 明顯錯誤時，可以按「校正目前 EXP」輸入正確值。

校正後程式會：

- 將目前 EXP 設為新的可信基準。
- 重新計算本次累積 EXP。
- 讓後續讀值以這筆資料為基準判斷是否合理。

### 校正等級

按「校正等級」輸入目前角色等級後，程式會使用內建 MapleStar 經驗表判斷：

- 目前 EXP 對應的百分比是否合理。
- 是否接近升級。
- 升級後的 EXP 歸零是否可信。
- OCR 是否可能把 `6` / `8` / `9` 看錯。

如果 OCR 的 EXP / 百分比看起來比較像別的等級，程式會在 OCR 診斷顯示提示，但不會只靠單筆讀值自動修改你的校正等級。

## 升級判斷邏輯

程式不會只看到 EXP 變低就立刻判定升級。現在會同時檢查：

- 上一筆 EXP 是否已接近該等級上限。
- 新 EXP 是否符合下一級的經驗表與百分比。
- OCR 百分比是否與視覺進度條接近。
- 新讀值是否穩定重複，或後續 EXP / 百分比是否有合理成長。

如果剛升級後短時間內 EXP 沒有增加，程式會先顯示「升級確認中」，等下一筆穩定樣本確認後才採用，避免把一筆錯誤 OCR 當成連續升級。

## OCR 誤判保護

### 6 / 8 / 9 混淆

楓之谷字型與遊戲縮放下，`6`、`8`、`9` 很容易互相看錯。程式會參考目前校正等級與百分比，嘗試只修正少數位數。

例如目前校正 Lv125，OCR 讀到：

```text
8,924,083 [31.87%]
```

但依照 Lv125 與約 31.9% 推算，較合理的是：

```text
9,924,083
```

程式會將第一位 `8` 修正為 `9`，並在 OCR 診斷中顯示修正原因。

### 上一筆低讀回補

如果上一筆因 OCR 看錯卡在 `8xx 萬`，下一筆恢復到 `1000 萬`，程式不會直接把整段差額算進下一秒效率。

它會先檢查上一筆是否可修正，例如：

```text
上一筆：8,924,083
下一筆：10,000,000
```

若依照等級與百分比可判斷上一筆應為：

```text
9,924,083
```

程式會先修正上一筆，再用：

```text
10,000,000 - 9,924,083
```

計算這次增量，避免效率爆衝。

## OCR 診斷怎麼看

右側「OCR 診斷」會顯示：

- 目前使用的 OCR 裝置。
- 截圖次數。
- 成功辨識次數。
- 已忽略異常次數。
- 上次取樣時間。
- 最後一筆 OCR 原始讀取與修正原因。

常見狀態：

- `已採用`：這筆讀值通過檢查並加入統計。
- `待確認`：可能是剛開始、疑似升級、或大型跳動，需要下一筆確認。
- `已忽略`：讀值不可信，已保留上一筆可信資料。
- `未讀到 EXP`：OCR 沒讀到可用數字，通常是框選範圍、畫面遮擋或解析度問題。
- `錯誤`：取樣或 OCR 過程發生例外。

## 從原始碼執行

在 Windows PowerShell 執行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe exp_tracker.py
```

確認 PP-OCRv5 可以初始化：

```powershell
.\.venv\Scripts\python.exe exp_tracker.py --self-test-ocr
```

結束碼 `0` 表示 OCR 初始化成功。

## 打包 Windows EXE

在 Windows PowerShell 執行：

```powershell
.\scripts\build_windows.ps1
```

輸出位置：

```text
dist\MapleStar-EXP-Tracker.exe
```

驗證打包後的 EXE：

```powershell
$p = Start-Process .\dist\MapleStar-EXP-Tracker.exe -ArgumentList "--self-test-ocr" -Wait -PassThru
$p.ExitCode
```

`0` 表示打包後的 EXE 可以正常初始化 OCR。

## 打包 macOS App / DMG

在 macOS 執行：

```bash
chmod +x scripts/build_macos_dmg.sh
./scripts/build_macos_dmg.sh
```

輸出位置：

```text
dist/MapleStar-EXP-Tracker.app
dist/MapleStar-EXP-Tracker.dmg
```

macOS 可能需要到系統設定中授權螢幕錄製與輔助使用權限。

## Windows 安全性提示

如果把自製 EXE 傳給別人，Windows 可能會顯示「不安全」或 SmartScreen 提醒。這通常不是程式一定有問題，而是因為：

- EXE 沒有程式碼簽章。
- 檔案下載次數少，沒有信譽紀錄。
- PyInstaller 打包的單檔 EXE 容易被防毒軟體提高警戒。

降低提醒的方法：

- 從公開 GitHub repo 或 GitHub Releases 發布。
- 提供 SHA256 雜湊讓使用者核對。
- 使用正式程式碼簽章憑證簽署 EXE。
- 避免用不明壓縮殼或二次加殼。

若只是自己或朋友使用，通常可以在 SmartScreen 提示中選擇「其他資訊」後執行；但正式公開發佈仍建議做程式碼簽章。

## 常見問題

### 為什麼讀值會跳來跳去？

OCR 會受字型、解析度、遊戲縮放、背景顏色、滑鼠指標、視窗遮擋影響。建議縮小框選範圍，只框 EXP 數字與百分比，並保持遊戲視窗不要頻繁移動。

### 為什麼已經升級了還顯示確認中？

升級後 EXP 會從高百分比變成低百分比，這種變化很像 OCR 大錯。程式會等下一筆穩定樣本確認，避免把錯誤讀值當成升級。

### 為什麼校正等級後，OCR 診斷說比較接近其他等級？

這代表目前 EXP / 百分比依照經驗表推算，和另一個等級更接近。程式只會提示，不會自動改掉你的校正等級。請確認目前等級與框選區域是否正確。

### 可以改成抓封包嗎？

不建議。這個工具目前只讀畫面。抓封包通常涉及加密協定、反作弊風險與遊戲規範問題，也不適合做成公開工具。

### 程式會修改遊戲或帳號資料嗎？

不會。程式只擷取你選定視窗的一小塊畫面做 OCR，不會寫入遊戲、不會注入程式、不會登入帳號。

## 專案結構

```text
exp_tracker.py                     主程式
requirements.txt                   執行需要的 Python 套件
requirements-build.txt             打包需要的 Python 套件
scripts/build_windows.ps1          Windows EXE 打包腳本
scripts/build_macos_dmg.sh         macOS App / DMG 打包腳本
packaging/windows-onefile.spec     PyInstaller Windows 設定
packaging/windows-version-info.txt Windows EXE 版本資訊
packaging/macos-app.spec           PyInstaller macOS 設定
assets/                            App icon
```

## 開發備註

- Windows `.exe` 請在 Windows 打包。
- macOS `.app` / `.dmg` 請在 macOS 打包。
- PyInstaller 不建議跨系統打包桌面 app。
- OCR 引擎目前固定使用 PP-OCRv5 + PaddleOCR CPU。

## 免責聲明

此專案為非官方工具，與 MapleStory Worlds、MapleStar 或相關遊戲營運方無關。使用者應自行確認工具使用方式是否符合遊戲規範與自身風險承受範圍。
