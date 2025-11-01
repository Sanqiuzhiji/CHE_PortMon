# PyQTGame

# 环境配置

## 1. 优先安装 PyCharm 2024.3.5 (Professional Edition),可通过官网下载安装,并使用学生信网申请免费一年使用权

## 2. 自行创建 Python 虚拟环境

## 3. 安装 Python 3.13.1

## 4. 安装 Qt Designer(最新版即可)

## 5. 安装 依赖包

```
pip install PyQt5==5.15.11
```

#### 目前安装的软件包有:

![软件包0.png](Readme/%E8%BD%AF%E4%BB%B6%E5%8C%850.png)

## 6. 配置外部工具

### 6.1. 配置 Qt Designer Edit

1. 打开 PyCharm -> Preferences -> Tools -> External Tools
2. 点击 + 按钮添加一个外部工具
3. 输入 名称: `Qt Designer Edit`
4. 输入 描述: `Qt Designer Edit`
5. 输入 程序: `designer.exe的路径`
6. 输入 实参: `$FileName$`
7. 输入 工作目录: `$FileDir$`
8. 勾选 在执行后同步文件
9. 勾选 打开工具输出的控制台
10. 点击 OK 保存设置

![外部工具0.png](Readme/%E5%A4%96%E9%83%A8%E5%B7%A5%E5%85%B70.png)

### 6.2. 配置 PYUIC5

1. 打开 PyCharm -> Preferences -> Tools -> External Tools
2. 点击 + 按钮添加一个外部工具
3. 输入 名称: `PYUIC5`
4. 输入 描述: `PYUIC5`
5. 输入 程序: `pyuic5.exe的路径`
6. 输入 实参: `$FileName$ -o $FileNameWithoutExtension$.py`
7. 输入 工作目录: `$FileDir$`
8. 勾选 在执行后同步文件
9. 勾选 打开工具输出的控制台
10. 点击 OK 保存设置

![外部工具1.png](Readme/%E5%A4%96%E9%83%A8%E5%B7%A5%E5%85%B71.png)

### 6.3. 配置 Qt Resources

1. 输入 名称: `Qt Resources`
2. 输入 描述: `Compile .qrc files to _rc.py using pyrcc5`
3. 输入 程序: `.venv\Scripts\pyrcc5.exe`
4. 输入 实参: `../assets/PtQtGame_Source.qrc -o PtQtGame_Source_rc.py`
5. 输入 工作目录: `$ProjectFileDir$\ui\`

![外部工具2.png](Readme/%E5%A4%96%E9%83%A8%E5%B7%A5%E5%85%B72.png)

### 6.4. 配置快捷键

![快捷键0.png](Readme/%E5%BF%AB%E6%8D%B7%E9%94%AE0.png)

![快捷键1.png](Readme/%E5%BF%AB%E6%8D%B7%E9%94%AE1.png)

## 常见的控件类型简写

| 控件类型 | 完整写法 | 推荐简写      | 说明 |
|---------|---------|-----------|------|
| QComboBox | comboBox | **cb**    | 组合框 |
| QPushButton | pushButton | **btn**   | 按钮 |
| QCheckBox | checkBox | **chk**   | 复选框 |
| QLineEdit | lineEdit | **ledit** | 单行文本框 |
| QTextEdit | textEdit | **tedit** | 多行文本框 |
| QLabel | label | **lbl**   | 标签 |
| QRadioButton | radioButton | **radio** | 单选按钮 |
| QSpinBox | spinBox | **spin**  | 数字微调框 |
