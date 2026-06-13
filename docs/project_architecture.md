# CHE_PortMon 工程框架说明

本文档用于说明当前工程框架的搭建方式、目录分层、核心模块职责、主要数据流，以及工程内各 Markdown 文档的位置。

## 工程整体定位

CHE_PortMon 当前是一个基于 PyQt5 的桌面串口工具，主要能力包括：

- 串口连接、参数配置、收发数据。
- 文本和 HEX 两种发送格式。
- 接收数据显示、HEX 显示、时间戳显示、自动滚动。
- 连续发送和重复发送。
- 自定义二进制协议编辑、导入、导出、保存和解析。
- JustFloat 数据解析并映射为实时通道。
- 绘图/控制面板布局管理。
- 滑块、模式等控件生成串口命令。
- 函数发生器生成点序列并通过串口发送。
- 深色/浅色主题切换。

工程整体采用较清晰的分层结构：

```text
启动入口
  -> 主窗口装配层
    -> 页面 UI 层
      -> 控制器层
        -> 服务层
          -> 数据模型层
          -> 配置文件/协议文件/布局文件
```

## 顶层目录结构

```text
CHE_PortMon/
├─ WindowManager.py
├─ README.md
├─ app/
├─ config/
├─ connections/
├─ controllers/
├─ docs/
├─ models/
├─ Readme/
├─ scripts/
├─ services/
├─ ui/
└─ utils/
```

## 启动入口

### WindowManager.py

位置：`WindowManager.py`

这是当前应用的直接启动入口，主要职责是：

- 创建 `QApplication`。
- 设置 Qt 应用风格为 `Fusion`。
- 创建主窗口 `MainWindow`。
- 设置主窗口初始位置。
- 显示主窗口。
- 进入 Qt 事件循环。

启动链路：

```text
WindowManager.py
  -> QApplication
  -> app.main_window.MainWindow
  -> main_window.show()
  -> app.exec_()
```

## 主窗口装配层

### app/

位置：`app/`

该目录承载主窗口级别的应用装配逻辑。

#### app/main_window.py

位置：`app/main_window.py`

`MainWindow` 是整个应用的核心协调者，负责把页面、控制器、服务和配置组合起来。

主要职责：

- 加载 `ui.generated.main_window_ui.Ui_MainWindow`。
- 初始化配置服务 `ConfigService`。
- 初始化主题服务 `ThemeService`。
- 初始化通道管理器 `ChannelManager`。
- 创建并注册各个功能页。
- 连接页面信号和主窗口槽函数。
- 应用主题和用户设置。
- 维护当前串口状态、收发统计、状态栏显示。
- 转发函数发生器和绘图控件生成的串口命令。

主窗口创建的页面包括：

| 页面 | 类 | 位置 |
| --- | --- | --- |
| 连接页 | `ConnectionPage` | `ui/pages/connection_page.py` |
| 绘图页 | `PlotPage` | `ui/pages/plot_page.py` |
| 协议编辑页 | `ProtocolEditorPage` | `ui/pages/protocol_editor_page.py` |
| 函数发生页 | `FunctionPage` | `ui/pages/function_page.py` |
| 设置页 | `SettingsPage` | `ui/pages/settings_page.py` |

主窗口中的典型数据转发：

```text
PlotPage.command_generated
  -> MainWindow._send_plot_command()
  -> UartController.send_bytes()
  -> SerialService.send_bytes()
```

```text
FunctionPage.send_requested
  -> MainWindow._start_function_send()
  -> QTimer 周期调用 _send_next_function_point()
  -> UartController.send_bytes()
```

## UI 层

### ui/

位置：`ui/`

UI 层负责界面文件、生成代码、页面行为、复用控件和主题样式。

```text
ui/
├─ forms/
├─ generated/
├─ pages/
├─ styles/
├─ widgets/
└─ windows/
```

### ui/forms/

位置：`ui/forms/`

该目录保存 Qt Designer 编辑出来的 `.ui` 原始文件。

当前主要文件：

| 文件 | 说明 |
| --- | --- |
| `main_window.ui` | 主窗口布局。 |
| `serial_page.ui` | 串口收发页面布局。 |
| `protocol_editor_page.ui` | 协议编辑页面布局。 |
| `function_page.ui` | 函数发生器页面布局。 |
| `settings_page.ui` | 设置页面布局。 |

这些文件通常由 Qt Designer 修改，然后通过脚本或 `pyuic5` 生成 Python UI 文件。

### ui/generated/

位置：`ui/generated/`

该目录保存由 `.ui` 文件生成的 Python UI 类。

当前主要文件：

| 文件 | 来源 |
| --- | --- |
| `main_window_ui.py` | 由 `ui/forms/main_window.ui` 生成。 |
| `serial_page_ui.py` | 由 `ui/forms/serial_page.ui` 生成。 |
| `protocol_editor_page_ui.py` | 由 `ui/forms/protocol_editor_page.ui` 生成。 |
| `function_page_ui.py` | 由 `ui/forms/function_page.ui` 生成。 |
| `settings_page_ui.py` | 由 `ui/forms/settings_page.ui` 生成。 |

注意：

- `ui/generated/` 中的文件一般不建议手工长期维护。
- 页面逻辑应写在 `ui/pages/`，而不是直接改生成文件。

### ui/pages/

位置：`ui/pages/`

该目录是页面行为层，负责把生成 UI 和业务信号封装成可被主窗口或控制器使用的页面类。

#### connection_page.py

位置：`ui/pages/connection_page.py`

连接页容器，当前注册 UART 页面。

主要职责：

- 创建 `UartConnectionPage`。
- 创建 `UartController`。
- 使用 `DetachableTabWidget` 管理连接类型页面。
- 对外暴露 UART 状态变化、统计变化、错误信号。
- 支持刷新串口、自动连接、刷新协议选项。

#### serial_page.py

位置：`ui/pages/serial_page.py`

串口收发页面，也定义了 `SerialPage = UartWidget` 兼容别名。

主要职责：

- 管理串口参数 UI，例如端口、波特率、数据位、校验位、停止位、RTS、DTR。
- 管理接收显示选项，例如 ABC/HEX、时间戳、自动滚动、显示模式。
- 管理发送格式，例如 ABC/HEX、行尾、连续发送、重复次数、发送间隔。
- 将用户操作转换成信号：
  - `refresh_ports_requested`
  - `open_port_requested`
  - `close_port_requested`
  - `send_data_requested`
  - `clear_receive_requested`
  - `save_receive_requested`
- 支持 `RawData`、`CustomBinary`、`JustFloat` 接收格式。
- 在 `CustomBinary` 模式下调用协议解析服务显示字段值。

#### plot_page.py

位置：`ui/pages/plot_page.py`

绘图/控制面板页面。

主要职责：

- 管理绘图工作页。
- 支持新增、删除、清空页面。
- 保存和导入布局 JSON。
- 管理网格大小和吸附设置。
- 挂载 `PlotCanvas`。
- 展示 `ChannelManager` 中的通道。
- 支持编辑通道名称、颜色、增益、偏移。
- 接收控件生成的命令并通过 `command_generated` 信号向主窗口发出。

#### protocol_editor_page.py

位置：`ui/pages/protocol_editor_page.py`

协议编辑页面的 UI 封装层。

主要职责：

- 加载 `Ui_ProtocolEditorPage`。
- 安装字段库 `FieldLibraryWidget`。
- 安装协议画布 `ProtocolCanvasWidget`。
- 安装属性面板 `ProtocolPropertyPanel`。
- 发出协议相关操作信号，例如新建、复制、删除、导入、导出、保存、生成代码。

实际协议操作由 `ProtocolEditorController` 完成。

#### function_page.py

位置：`ui/pages/function_page.py`

函数发生器页面。

主要职责：

- 收集函数参数。
- 请求预览点序列。
- 请求开始发送。
- 请求停止发送。
- 显示函数曲线。

实际点生成由 `utils/function_generator.py` 完成，周期发送由 `MainWindow` 中的 `QTimer` 协调。

#### settings_page.py

位置：`ui/pages/settings_page.py`

设置页面。

主要职责：

- 显示和编辑主题。
- 显示和编辑默认波特率。
- 设置是否自动连接。
- 设置默认保存路径。
- 将设置打包成 `AppSettings` 后通过 `save_requested` 信号交给主窗口保存。

### ui/widgets/

位置：`ui/widgets/`

该目录保存复用型控件。

主要文件：

| 文件 | 说明 |
| --- | --- |
| `plot_widgets.py` | 绘图画布和控制控件，例如滑块、模式控件、可拖拽/可缩放控件等。 |
| `protocol_editor_widgets.py` | 协议编辑器控件，包括字段库、协议画布、属性面板。 |
| `detachable_tab_widget.py` | 可分离连接 Tab 控件。 |
| `detachable_page_tab_widget.py` | 可分离页面 Tab 控件。 |

### ui/windows/

位置：`ui/windows/`

该目录保存独立窗口或浮动窗口。

主要文件：

| 文件 | 说明 |
| --- | --- |
| `uart_window.py` | UART 独立窗口相关逻辑。 |
| `floating_page_window.py` | 浮动页面窗口。 |
| `floating_connection_window.py` | 浮动连接窗口。 |

### ui/styles/

位置：`ui/styles/`

主题样式目录。

| 文件 | 说明 |
| --- | --- |
| `dark.qss` | 深色主题。 |
| `light.qss` | 浅色主题。 |

主题通过 `services/theme_service.py` 加载并应用。

## 控制器层

### controllers/

位置：`controllers/`

控制器层用于连接页面信号和服务层逻辑，避免页面类直接承担过多业务流程。

### controllers/uart_controller.py

位置：`controllers/uart_controller.py`

UART 控制器，连接 UART 页面和串口服务。

主要职责：

- 响应页面请求刷新串口。
- 打开和关闭串口。
- 发送字节数据。
- 清空接收数据。
- 保存接收文本。
- 监听 `SerialService` 的数据接收、打开、关闭、错误、统计信号。
- 将串口状态变化转发给主窗口。
- 在 `JustFloat` 模式下将接收数据解析为通道值并更新 `ChannelManager`。

核心链路：

```text
UartWidget.send_data_requested
  -> UartController.send_bytes()
  -> SerialService.send_bytes()
```

```text
SerialService.data_received
  -> UartController._handle_received_data()
  -> UartWidget.append_received_data()
  -> JustFloatParser.feed()
  -> ChannelManager.update_values()
```

### controllers/protocol_editor_controller.py

位置：`controllers/protocol_editor_controller.py`

协议编辑控制器，连接协议编辑页面和协议服务。

主要职责：

- 加载协议列表。
- 新建协议。
- 复制协议。
- 删除协议。
- 导入协议。
- 导出协议。
- 保存协议。
- 生成解析代码。
- 响应协议选中、字段选中、拖拽排序。
- 更新协议属性和字段属性。
- 自动重新计算字段字节范围。

核心链路：

```text
ProtocolEditorPage 操作信号
  -> ProtocolEditorController
  -> ProtocolService
  -> config/protocols/*.json
```

## 服务层

### services/

位置：`services/`

服务层承载可复用的业务能力和持久化能力。

### services/serial_service.py

位置：`services/serial_service.py`

底层串口服务，基于 `PyQt5.QtSerialPort.QSerialPort`。

主要职责：

- 枚举可用串口。
- 打开串口。
- 关闭串口。
- 配置波特率、校验位、数据位、停止位、RTS、DTR。
- 写入字节数据。
- 读取接收数据。
- 维护收发字节统计。
- 发出串口错误信号。

### services/config_service.py

位置：`services/config_service.py`

应用配置服务。

主要职责：

- 读取 `config/app_settings.json`。
- 文件不存在时生成默认配置。
- 配置损坏或 JSON 解析失败时回退默认配置。
- 保存 `AppSettings`。

### services/theme_service.py

位置：`services/theme_service.py`

主题服务。

主要职责：

- 根据设置选择深色或浅色主题。
- 加载 `ui/styles/dark.qss` 或 `ui/styles/light.qss`。
- 应用到 `QApplication` 或窗口实例。

### services/protocol_service.py

位置：`services/protocol_service.py`

协议文件管理服务。

主要职责：

- 管理 `config/protocols/` 目录。
- 确保示例协议存在。
- 列出协议。
- 加载协议。
- 保存协议。
- 新建协议。
- 复制协议。
- 删除协议。
- 导入协议。
- 导出协议。
- 将协议名称转换成安全文件名。

### services/protocol_parse_service.py

位置：`services/protocol_parse_service.py`

协议解析服务。

主要职责：

- 根据协议字段定义解析 payload。
- 只解析 `kind == "Data"` 的字段。
- 按字段 `start/end` 截取字节。
- 支持常见类型解析，例如 `uint8`、`uint16`、`uint32`、`float`、`double`、`string`。
- 根据协议字节序选择大端或小端。

### services/protocol_codegen_service.py

位置：`services/protocol_codegen_service.py`

协议代码生成服务。

主要职责：

- 根据当前协议定义生成解析器代码。
- 供协议编辑页面的“生成代码/测试解析”功能使用。

### services/plot_layout_service.py

位置：`services/plot_layout_service.py`

绘图布局服务。

主要职责：

- 读取 `config/plot_layout.json`。
- 文件不存在时创建默认布局。
- 保存当前绘图页面、控件位置、控件大小、控件配置。
- 从外部 JSON 导入布局。
- 将布局导出到指定路径。

### services/channel_manager.py

位置：`services/channel_manager.py`

通道管理服务。

主要职责：

- 保存当前通道状态。
- 根据 JustFloat 解析结果动态创建或更新通道。
- 维护通道 key、名称、颜色、原始值、启用状态。
- 支持更新通道名称、颜色、增益、偏移。
- 通过 `channels_changed` 信号通知绘图页面刷新。

### services/just_float_parser.py

位置：`services/just_float_parser.py`

JustFloat 数据解析器。

主要职责：

- 从 UART 接收字节流中解析浮点帧。
- 输出一组浮点值。
- 供 `UartController` 更新实时通道。

### services/port_scan_thread.py

位置：`services/port_scan_thread.py`

串口扫描线程。

主要职责：

- 在后台扫描串口。
- 避免串口扫描阻塞 UI。

## 数据模型层

### models/

位置：`models/`

模型层保存业务数据结构，主要使用 dataclass。

### models/app_settings.py

位置：`models/app_settings.py`

应用设置模型。

字段包括：

| 字段 | 说明 |
| --- | --- |
| `theme` | 当前主题，支持 `dark` 和 `light`。 |
| `default_baudrate` | 默认波特率。 |
| `auto_connect` | 是否启动后自动连接。 |
| `default_save_path` | 默认保存路径。 |

同时提供 `normalize_theme()`，用于兼容不同主题文本别名。

### models/serial_config.py

位置：`models/serial_config.py`

串口配置模型。

主要包含：

- 端口名。
- 波特率。
- 校验位。
- 数据位。
- 停止位。
- RTS。
- DTR。

也包含接收显示相关选项模型。

### models/protocol_model.py

位置：`models/protocol_model.py`

协议模型。

核心结构：

```text
ProtocolDefinition
  -> ProtocolFrame
    -> ProtocolField
```

主要类：

| 类 | 说明 |
| --- | --- |
| `ProtocolDefinition` | 一个完整协议定义，包含协议名称、代码模式、字节序、校验方式和帧列表。 |
| `ProtocolFrame` | 一帧协议结构，包含字段列表。 |
| `ProtocolField` | 单个字段，包含 label、kind、data_type、length、start、end、默认值、颜色、是否参与校验。 |

`ProtocolFrame.recalculate_ranges()` 会根据字段长度自动计算每个字段的 `start` 和 `end`。

### models/channel_model.py

位置：`models/channel_model.py`

实时通道模型。

主要内容：

- 通道索引。
- 通道 key，例如 `CH0`、`CH1`。
- 通道名称。
- 通道颜色。
- 原始值。
- 增益。
- 偏移。
- 启用状态。
- 显示值。

显示值通常由原始值、增益和偏移计算得到。

## 配置与数据文件

### config/

位置：`config/`

该目录保存运行时配置、协议定义和绘图布局。

```text
config/
├─ app_settings.json
├─ plot_layout.json
└─ protocols/
   ├─ Test_Protocol.json
   └─ Test_Protocol2.json
```

### config/app_settings.json

位置：`config/app_settings.json`

应用设置文件。

当前字段：

```json
{
  "theme": "dark",
  "default_baudrate": "115200",
  "auto_connect": false,
  "default_save_path": "G:/Desk/Common_Folders/CHE_PortMon"
}
```

由 `ConfigService` 读写，由 `SettingsPage` 展示和修改。

### config/plot_layout.json

位置：`config/plot_layout.json`

绘图布局文件。

主要保存：

- 页面列表。
- 页面名称。
- 网格大小。
- 是否吸附网格。
- 控件列表。
- 控件类型。
- 控件位置。
- 控件尺寸。
- 控件配置。

由 `PlotLayoutService` 读写，由 `PlotPage` 使用。

### config/protocols/

位置：`config/protocols/`

协议定义文件目录。

当前示例：

| 文件 | 说明 |
| --- | --- |
| `Test_Protocol.json` | 示例协议定义。 |
| `Test_Protocol2.json` | 示例协议定义。 |

协议文件由 `ProtocolService` 管理，由协议编辑器和自定义二进制解析功能使用。

## 连接抽象层

### connections/

位置：`connections/`

该目录保存连接相关抽象。

主要文件：

| 文件 | 说明 |
| --- | --- |
| `base_connection.py` | 连接基类或通用接口。 |
| `uart_connection.py` | UART 连接实现。 |

当前主流程主要还是通过 `SerialService` 和 `UartController` 完成串口连接，`connections/` 更像是为后续扩展不同连接类型预留的抽象层。

## 工具层

### utils/

位置：`utils/`

工具层保存通用辅助函数。

主要文件：

| 文件 | 说明 |
| --- | --- |
| `format_utils.py` | 文本、HEX、字节、时间戳等格式转换工具。 |
| `file_utils.py` | 文件相关辅助函数。 |
| `function_generator.py` | 函数点序列生成工具。 |

其中 `format_utils.py` 被串口发送、接收显示、HEX 转换等功能广泛使用。

## 脚本目录

### scripts/

位置：`scripts/`

脚本目录用于工程辅助构建。

#### scripts/build_ui.py

位置：`scripts/build_ui.py`

用于将 `ui/forms/*.ui` 转换为 `ui/generated/*_ui.py`。

推荐的 UI 修改流程：

```text
Qt Designer 修改 ui/forms/*.ui
  -> 运行 scripts/build_ui.py 或 pyuic5
  -> 更新 ui/generated/*_ui.py
  -> 在 ui/pages/*.py 中编写页面逻辑
```

## README 图片资源目录

### Readme/

位置：`Readme/`

该目录当前保存 `README.md` 中引用的图片资源。

主要资源类型：

- 软件包截图。
- 外部工具配置截图。
- 快捷键配置截图。

注意该目录名称虽然是 `Readme`，但它当前不是 Markdown 文档目录。

## 主要业务流程

### 应用启动流程

```text
WindowManager.py
  -> 创建 QApplication
  -> 创建 MainWindow
  -> MainWindow 加载 Ui_MainWindow
  -> MainWindow 创建 ConfigService / ThemeService / ChannelManager
  -> MainWindow 创建各功能页面
  -> MainWindow 连接页面信号
  -> 应用主题和设置
  -> 刷新串口
  -> 显示主窗口
```

### UART 打开流程

```text
用户点击连接
  -> UartWidget 发出 open_port_requested
  -> UartController.open_port()
  -> SerialService.open_port()
  -> QSerialPort.open()
  -> SerialService.opened
  -> UartController._handle_opened()
  -> UartWidget.set_connected(True)
  -> MainWindow 更新状态栏
```

### UART 发送流程

```text
用户输入发送内容
  -> UartWidget 根据 ABC/HEX 格式转换为 bytes
  -> UartWidget 发出 send_data_requested
  -> UartController.send_bytes()
  -> SerialService.send_bytes()
  -> QSerialPort.write()
  -> 更新发送字节统计
```

### UART 接收流程

```text
串口收到数据
  -> QSerialPort.readyRead
  -> SerialService._read_data()
  -> SerialService.data_received
  -> UartController._handle_received_data()
  -> UartWidget.append_received_data()
  -> 根据显示模式渲染接收文本
```

如果当前数据格式为 `JustFloat`：

```text
UartController._handle_received_data()
  -> JustFloatParser.feed()
  -> ChannelManager.update_values()
  -> PlotPage / PlotChannelPanel 刷新通道显示
```

### 自定义协议解析流程

```text
用户选择 CustomBinary
  -> 用户选择协议
  -> UART 接收数据
  -> UartWidget._format_custom_binary_chunk()
  -> ProtocolService.load_protocol()
  -> ProtocolParseService.parse_data_fields()
  -> 接收窗口显示字段名和值
```

### 协议编辑流程

```text
ProtocolEditorPage 发出操作信号
  -> ProtocolEditorController
  -> ProtocolService 读写协议 JSON
  -> ProtocolDefinition / ProtocolFrame / ProtocolField 更新
  -> ProtocolEditorPage 刷新协议画布和属性面板
```

### 绘图布局流程

```text
启动 PlotPage
  -> PlotLayoutService.ensure_default_layout()
  -> 读取 config/plot_layout.json
  -> 创建页面和控件
  -> 用户调整布局
  -> PlotPage.save_layout()
  -> PlotLayoutService.save_layout_to()
```

### 绘图控件发送命令流程

```text
用户操作 PlotCanvas 上的控件
  -> 控件生成 PlotCommand
  -> PlotCanvas.command_generated
  -> PlotPage.command_generated
  -> MainWindow._send_plot_command()
  -> UartController.send_bytes()
  -> SerialService.send_bytes()
```

### 函数发生器发送流程

```text
用户设置函数参数
  -> FunctionPage.preview_requested
  -> MainWindow._preview_function()
  -> utils.function_generator.generate_function_points()
  -> FunctionPage.plot_points()
  -> 用户点击发送
  -> MainWindow._start_function_send()
  -> QTimer 周期发送点值
  -> UartController.send_bytes()
```

## 当前架构特点

当前工程已经具备以下特点：

- UI 原始文件和生成文件分离。
- 页面逻辑和生成 UI 分离。
- 页面层通过信号与控制器层通信。
- 控制器层负责串联 UI 和服务。
- 服务层负责串口、配置、协议、布局等业务能力。
- 模型层使用 dataclass 表达配置、协议、通道等结构。
- 配置、协议、布局均使用 JSON 持久化。
- 绘图页面和 UART 接收通过 `ChannelManager` 解耦。
- 主窗口统一协调跨页面操作，例如绘图命令发送和函数发生器发送。

## 后续文档建议

建议后续 Markdown 文档统一放在 `docs/` 目录：

| 建议文件 | 建议位置 | 内容 |
| --- | --- | --- |
| development_guide.md | `docs/development_guide.md` | 开发环境、运行方式、UI 构建方式、常见问题。 |
| protocol_format.md | `docs/protocol_format.md` | 协议 JSON 字段格式、字段类型、校验方式。 |
| uart_workflow.md | `docs/uart_workflow.md` | 串口连接、发送、接收、解析流程说明。 |
| plot_layout_format.md | `docs/plot_layout_format.md` | 绘图布局 JSON 结构和控件配置说明。 |

