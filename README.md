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
python jomoo_toilet.py raw [resp] [ffe1|f001] <hex...>   # 发送任意原始帧

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

# 动作（自动先读状态，防止覆盖其他设置）
python jomoo_toilet.py act bigflush           # 大冲
python jomoo_toilet.py act flush-small        # 小冲
python jomoo_toilet.py act cover-open / cover-close / cover-openring
python jomoo_toilet.py act wash-hip / wash-woman / wash-auto-hip / wash-auto-woman
python jomoo_toilet.py act dry / defecate / sitz / nozzle-clean / deodorize / autotemp / stop

# 设置（自动先读状态，只改指定项）
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

3. 设置类命令会先发送查询帧（`E2`）读取当前状态，按位修改目标项后发送，
   避免把其他设置覆盖为默认值。

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
