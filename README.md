# PDF → 3D 空间可视化

上传室内设计 PDF 图纸，自动解析尺寸数据，即时生成可交互的 3D 模型。

## 功能

- **PDF 智能解析** — 自动识别页面类型（平面图/立面图/柜体图），按房间分组
- **实时 3D 渲染** — 拖放 PDF 即刻生成可旋转、缩放、平移的 3D 模型
- **多房间布局** — 自动排列厨房、客厅、卧室、书房等空间位置
- **柜体建模** — 从图纸尺寸标注中提取柜体宽高深，可视化展示
- **AI 视觉解析** — 可选启用 Claude Vision API 进行精确尺寸识别，比文本解析更精细
- **材质区分** — 不同房间使用独立配色，柜体与墙体材质区分

## 安装

```bash
# 克隆项目
cd 3D_model

# 创建虚拟环境
python -m venv venv
source venv/Scripts/activate  # Windows
# source venv/bin/activate     # macOS/Linux

# 安装依赖
pip install flask numpy PyMuPDF

# 启动服务
python -m src.webui.app
```

打开浏览器访问 `http://localhost:5000`，拖放 PDF 文件即可。

## 使用方法

1. 打开 `http://localhost:5000`
2. 拖放 PDF 图纸到上传区域（或点击选择文件）
3. 等待解析完成（约 1-3 秒）
4. 使用鼠标交互查看 3D 模型

### 操作快捷键

| 键 | 功能 |
|----|------|
| 鼠标左键拖拽 | 旋转视角 |
| 鼠标滚轮 | 缩放 |
| 鼠标右键拖拽 | 平移 |
| `1` `2` `3` `4` | 透视图 / 俯视图 / 前视图 / 右视图 |
| `W` | 线框模式 |

## 架构

```
拖放 PDF
    │
    ▼
┌─────────────────┐
│   Flask API      │  POST /api/parse
│   接收 PDF 文件   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   PDF 解析器     │  PyMuPDF
│   reader.py      │  提取矢量线段 + 文字
│   classifier.py  │  页面分类 + 房间分组
│   assembler.py   │  构建房间/柜体 JSON
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   3D 渲染器      │  Three.js
│   viewer.html    │  墙体/地板/柜体几何体
│                  │  OrbitControls 交互
└─────────────────┘
```

## 项目结构

```
3D_model/
├── README.md
├── environment.yml              # conda 环境配置
├── run.py                       # 快捷脚本
├── src/
│   ├── schema.py                # JSON 数据验证
│   ├── parser/                  # PDF 解析模块
│   │   ├── reader.py            #   PyMuPDF 读取
│   │   ├── classifier.py        #   页面分类 + 房间分组
│   │   ├── assembler.py         #   房间/柜体 JSON 构建
│   │   └── cli.py               #   命令行工具
│   ├── webui/                   # Web 应用
│   │   ├── app.py               #   Flask 服务
│   │   └── templates/
│   │       └── viewer.html      #   Three.js 前端
│   ├── modeler/                 # Blender 建模（可选）
│   └── preview/                 # 静态预览页
├── data/
│   ├── input/                   # 输入 PDF
│   ├── parsed/                  # 解析结果 JSON
│   └── output/                  # 渲染输出
└── tests/                       # 测试
```

## 技术栈

| 层 | 技术 |
|----|------|
| PDF 解析 | PyMuPDF (fitz) |
| Web 后端 | Flask |
| 3D 渲染 | Three.js + OrbitControls |
| 字体 | Outfit, Crimson Text, DM Mono |
| 环境 | Python 3.9+, venv/conda |

## AI 视觉解析模式

启用 Claude Vision API 可获得更精确的尺寸识别：

```bash
# 设置 API Key
export ANTHROPIC_API_KEY=sk-ant-...

# 启动服务（自动启用视觉模式）
python -m src.webui.app
```

在 Web 界面中切换到 **"AI 视觉"** 模式，上传 PDF 后 Claude 会将每页渲染为图像进行分析，识别：
- 尺寸线和标注数字的精确对应关系
- 房间/柜体的真实几何结构
- 材质标注和设计说明

视觉模式处理速度约 10-30 秒/批（3 页），比文本模式慢但精度更高。

## 命令行工具

```bash
# 仅解析 PDF 输出 JSON（不启动 Web 服务）
python -m src.parser.cli input.pdf output.json

# Blender 离线渲染（需安装 Blender）
blender --background --python src/modeler/build_model.py -- data/parsed/model.json data/output/
```
