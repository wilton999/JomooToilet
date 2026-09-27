# 九牧智联马桶 BLE 控制工具（非官方）

在电脑（Windows / macOS / Linux）上通过蓝牙 BLE 控制九牧智能马桶。**当前仅针对 ZS781J（型号码 279331）**。

协议通过对微信小程序「九牧智联」的蓝牙通信进行分析得出，本项目为**独立实现的互操作工具**，不包含任何原小程序代码、图片或数据。

> ⚠️ 仅供控制**你自己的设备**使用。本项目与九牧（JOMOO）官方无任何关系，非官方工具。

---

## 功能

```powershell
python jomoo_toilet.py scan                   # 扫描附近的 JOMOO 马桶
python jomoo_toilet.py query                  # 读取马桶当前设置
python jomoo_toilet.py listen [秒]            # 监听所有通知（默认10秒）
python jomoo_toilet.py raw [norsp] [ffe1|f001] <hex...>   # 发送任意原始帧（默认带响应写）
python jomoo_toilet.py multi "foot off" "set autocover off"   # 一次连接依次执行多条命令

# 开关类
python jomoo_toilet.py foot on/off            # 脚感控制
python jomoo_toilet.py uv on/off              # 水路UV杀菌
python jomoo_toilet.py atmo on/off            # 氛围灯（atmo-mode <模式> 带模式）
python jomoo_toilet.py bubble on/off          # 自动发泡
python jomoo_toilet.py openbubble on/off      # 开圈发泡
python jomoo_toilet.py bubblerun              # 立即启动魔力泡
python jomoo_toilet.py prewet on/off          # 预湿润
python jomoo_toilet.py closeflush on/off      # 关盖冲厕
python jomoo_toilet.py smallflush on/off      # 自动小冲
python jomoo_toilet.py closesmallflush on/off # 关盖自动小冲
python jomoo_toilet.py filter on/off          # 滤芯提醒（on=复位并开启）
python jomoo_toilet.py aivoice on/off         # AI语音
python jomoo_toilet.py petwash on/off         # 宠物清洗
python jomoo_toilet.py selfclean on/off       # 自清洁
python jomoo_toilet.py regularselfclean on/off # 定期自清洁
python jomoo_toilet.py nozzledry / autonozzledry on/off   # 喷杆干燥
python jomoo_toilet.py sens 0|1               # 翻盖灵敏度
python jomoo_toilet.py dist <数值>            # 翻盖感应距离
python jomoo_toilet.py bright <数值>          # 夜灯亮度
python jomoo_toilet.py strongdry <数值>       # 强力烘干
python jomoo_toilet.py brushtime <数值>       # 刷圈发泡时间档
python jomoo_toilet.py redblue <模式> <红> <蓝>   # 红蓝光
python jomoo_toilet.py liftclean / liquidbox / forceflush / unblock

# 动作（优先用本地状态缓存，防止覆盖其他设置；写入后自动校验）
python jomoo_toilet.py act bigflush           # 大冲
python jomoo_toilet.py act flush-small        # 小冲
python jomoo_toilet.py act cover-open / cover-close / cover-openring
python jomoo_toilet.py act wash-hip / wash-woman / wash-auto-hip / wash-auto-woman
python jomoo_toilet.py act dry / defecate / sitz / nozzle-clean / deodorize / autotemp / stop

# 设置（优先用本地状态缓存，只改指定项；写入后自动校验、失败自动重试）
python jomoo_toilet.py set autoflush on       # 自动冲刷
python jomoo_toilet.py set autocover on       # 自动翻盖
python jomoo_toilet.py set seat 2             # 座温（0-15）；water 水温；air 风温
python jomoo_toilet.py set hippress 5         # 臀洗水压；hipnozzle 喷嘴位置；widewash 宽幅
```

## 安装

1. Python 3.10+（开发环境 3.14）
2. `pip install bleak`
3. 电脑需带蓝牙并已打开

## 设备匹配

默认自动扫描名字以 `JOMOO_SMART` 开头的设备，多台时选信号最强的一台并打印列表。

首次扫描到设备后，会把设备地址记录到脚本目录的 `toilet_mac.txt`；之后每次启动
直接按记录的地址连接，**跳过扫描环节**（更快）。换设备或找不到时删除该文件即可
重新扫描。

如需固定指定设备（可选）：

```powershell
$env:JOMOO_MAC = "AA:BB:CC:DD:EE:FF"
```

> `toilet_mac.txt` 只存在于本地，包含你的设备地址，已在 `.gitignore` 中排除，
> 请勿提交到公开仓库。

---

## 一次执行多条命令（multi）

每次运行都重新扫描/连接设备比较慢，用 `multi` 可以在**同一次蓝牙连接**里依次执行多条命令：

```powershell
python jomoo_toilet.py multi "foot off" "set autocover off" "bright 2"
python jomoo_toilet.py multi "foot off; set autocover off"   # 等价的写法
```

* 每个带引号的参数算一条命令；一个参数里也可以用 `;` 分隔多条。
* 命令按顺序执行；某条出错（例如写错命令）只会打印提示，不影响后续命令。
* `set` / `act` 优先使用本地状态缓存 `toilet_state.json`（收到 E2/FA 状态帧时自动更新），
  无需每次查询；确实需要时才查询，并在写入后校验、失败自动重试（最多 3 次）。
* 支持 `sleep <秒>` 命令控制两条命令之间的间隔，例如
  `multi "query" "sleep 3" "set autocover off"`。
* `multi` 也可以写成 `batch`。

---

## 定时任务（例如每天定时开关脚感）

Windows 下提供 `setup_schedule.ps1`，可一键注册/删除两个计划任务：
每天 `21:00` 关闭脚感（`foot off`），`23:00` 打开脚感（`foot on`）。

```powershell
# 安装（默认 21:00 关、23:00 开）
powershell -ExecutionPolicy Bypass -File .\setup_schedule.ps1

# 自定义时间与命令（例如晚上关脚感+关自动翻盖，早上恢复）
powershell -ExecutionPolicy Bypass -File .\setup_schedule.ps1 -OffTime 22:00 -OnTime 07:00 `
  -OffCommand 'multi "foot off" "set autocover off"' -OnCommand 'multi "foot on" "set autocover on"'

# 删除任务
powershell -ExecutionPolicy Bypass -File .\setup_schedule.ps1 -Remove
```

说明：

* 默认两个任务分别是 `foot off` / `foot on`，可用 `-OffCommand` / `-OnCommand`
  改成任意命令（多条命令用 `multi`，见上节）。
* 任务以当前用户身份运行，仅在用户登录时执行（BLE 需要用户会话）。
* 通过 `pythonw` + `run_silent.pyw` 静默运行，不会弹出黑色控制台窗口。
* 电脑睡眠时会唤醒执行；错过的时间点会在开机后自动补跑。
* 每次运行日志追加到 `logs\foot_off.log` / `logs\foot_on.log`，连不上马桶时可在其中查看原因。

---

## 协议摘要

1. 该控制器使用的蓝牙服务：
   
   * `0000FFE0`（服务）/ `0000FFE1`（写 + 通知）
   - 另有 `0000F000/F001/F002` 通讯通道（本工具暂未使用）

2. 帧格式（F3F4 协议族）：
   
   | 类型         | 格式                                       |
   | ---------- | ---------------------------------------- |
   | 10 字节开关    | `F3 F4 06 92 21 1F <cmd> <val> <校验> FC`  |
   | 19 字节动作/设置 | `F3 F4 0F 92 21 <code> <状态位×11> <校验> FC` |
   | 查询状态       | `F3 F4 08 92 00 E2 00 00 00 00 <校验> FC`  |
   
   校验算法：从长度字节起、到校验位前（不含）的所有字节求和，取低 8 位。

3. 可靠性设计（已实测验证）：
   * 所有写入都使用**带响应写**（Write Request），与小程序行为一致；
     用无响应写发送 19 字节设置帧会被设备忽略。
   * 设备在刚回复状态查询（E2）后的短时间内会忽略设置帧；因此工具在必须
     查询的情况下会先等待约 3 秒再发送。
   * 设置类命令优先使用本地状态缓存 `toilet_state.json`（每次收到 E2/FA
     状态帧自动更新），据此按位修改，避免覆盖其他设置。
   * 设置帧发送后会自动查询校验，未生效则自动重发（最多 3 次）。

4. 马桶通常会对命令回发状态帧（`FA`/`E7`/`E9` 等），工具会打印出来供确认。

### ZS781J 适用的命令（部分实测）

| 功能                        | 命令                                |
| ------------------------- | --------------------------------- |
| 脚感                        | `1F 24`，开=1 关=2（实测 ✅）             |
| UV杀菌                      | `1F 21`，开=0x40 关=0x20（实测 ✅）       |
| 氛围灯                       | `1F 33`，开=0x20 关=0x10（可\|模式）      |
| 自动发泡                      | `1F 20`，开=2 关=4；启动=1；开圈=0x20/0x40 |
| 预湿润                       | `1F 30`，开=4 关=0                   |
| 关盖冲厕/自动小冲/关盖自动小冲          | `1F 25`，1/2、4/8、16/32             |
| 滤芯提醒                      | `1F C7`，1=复位并开，2=关                |
| 夜灯亮度/强力烘干                 | `1F 2A` / `1F 22`                 |
| 各动作（大冲14/小冲15/开盖17/关盖16…） | 19 字节帧 `<code>`                   |
| 设置同步（座温/水温/风速/翻盖等）        | 19 字节帧 code=25                    |

## 限制与已知约束

1. **仅适配 ZS781J**（型号码 279331，`bleProtocol: 0`，F3F4 协议族）。
   同协议族型号理论上可用（脚感等命令结构一致），但未验证。
2. 不支持其他协议族型号。
3. 需要电脑蓝牙，设备大致在 5~10 米内；Windows 下扫描偶发失败（内置重试）。
4. 本工具只走本地 BLE，不涉及账号/云端。
5. 部分功能取决于固件实际支持（例如 ZS781J 没有"自动除臭/微波/恢复出厂"等）。
6. 未实现 OTA 升级。
7. 本设备 BLE **无配对与鉴权**：请仅在自有设备上使用本工具。

## 许可证

本项目采用 MIT 许可证，详见 [LICENSE](LICENSE)。

## 免责声明

- 本项目为个人互操作研究产物，为独立实现，不包含原小程序代码。
- 「九牧 / JOMOO」为九牧公司商标，本项目为非官方兼容工具，与其无任何关联。
- **本工具不保证对设备没有任何损害**：不同型号/固件对命令的响应可能不同，
  请确认风险后再使用；**一切风险与后果由使用者自行承担**，作者不承担任何责任。
- 请勿将本工具用于他人设备或任何未授权用途。
