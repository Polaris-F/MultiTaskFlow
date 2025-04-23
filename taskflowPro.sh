#!/bin/bash

#======= 用户可配置变量 =======
# 配置你的conda环境名称
CONDA_ENV="pytorch24"
# 配置你的主脚本名称（如果不使用shell命令）
SCRIPT_NAME="MultiTaskFlow.py"
# 配置PID文件名称
PID_FILE_NAME="multitaskflow.pid"
# 任务配置文件路径（完整路径，例如：/path/to/your/TaskFlow.yaml）
TASK_CONFIG="path/to/your/TaskFlow.yaml"
# 配置等待时间（秒）
WAIT_TIME=3
#============================

# 定义颜色输出
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # 无颜色

# 检查命令行参数
if [ $# -lt 1 ]; then
    echo -e "${RED}错误: 缺少操作参数${NC}"
    echo -e "用法: $0 [start|stop] [配置文件路径]"
    echo -e "示例: $0 start"
    echo -e "      $0 stop"
    echo -e "      $0 start /path/to/your/CustomTask.yaml"
    exit 1
fi

ACTION=$1
shift  # 移除第一个参数

# 检查是否有自定义配置文件路径
if [ $# -gt 0 ]; then
    TASK_CONFIG="$1"
fi

## 获取当前脚本所在目录
current_dir=$(cd $(dirname $0); pwd)
echo -e "${BLUE}当前脚本目录: ${current_dir}${NC}"

## 检查配置文件并设置工作目录
if [ -z "$TASK_CONFIG" ]; then
    echo -e "${RED}错误: 未指定任务配置文件路径${NC}"
    exit 1
fi

if [ ! -f "$TASK_CONFIG" ]; then
    echo -e "${RED}错误: 配置文件 '$TASK_CONFIG' 不存在${NC}"
    exit 1
fi

# 提取配置文件所在目录作为工作目录
target_dir=$(dirname "$TASK_CONFIG")
config_file=$(basename "$TASK_CONFIG")
echo -e "${BLUE}任务配置文件: ${TASK_CONFIG}${NC}"
echo -e "${BLUE}工作目录: ${target_dir}${NC}"

## 日志目录和PID文件路径
log_dir="${target_dir}/logs"
pid_file="${log_dir}/${PID_FILE_NAME}"

## 根据操作执行不同功能
case $ACTION in
    start)
        # 启动任务函数
        ## 获取当前日期
        current_date=$(date +%Y%m%d)
        echo -e "${BLUE}运行日期: ${current_date}${NC}"

        ## 检查日志目录
        if [ ! -d "$log_dir" ]; then
            mkdir -p "$log_dir"
            echo -e "${BLUE}创建日志目录: ${log_dir}${NC}"
        fi

        ## 日志文件名
        log_file="${log_dir}/TaskFlow_${current_date}.log"
        echo -e "${BLUE}日志将保存至: ${log_file}${NC}"

        ## 激活conda环境
        echo -e "${BLUE}正在激活conda环境 '${CONDA_ENV}'...${NC}"
        source $(conda info --base)/etc/profile.d/conda.sh
        conda activate $CONDA_ENV || { echo -e "${YELLOW}conda环境 '${CONDA_ENV}' 激活失败，尝试继续执行...${NC}"; }

        # 检查是否存在taskflow命令
        if command -v taskflow &> /dev/null; then
            echo -e "${GREEN}发现taskflow命令，使用shell命令运行${NC}"
            CMD="cd ${target_dir} && taskflow ${config_file}"
        else
            # 检查脚本是否存在
            if [ ! -f "${target_dir}/${SCRIPT_NAME}" ]; then
                echo -e "${YELLOW}警告: ${target_dir}/${SCRIPT_NAME} 文件不存在!${NC}"
                exit 1
            fi
            echo -e "${GREEN}使用Python脚本运行${NC}"
            CMD="cd ${target_dir} && python ${SCRIPT_NAME} ${config_file}"
        fi

        ## 运行脚本并保存PID
        echo -e "${GREEN}启动任务流管理器...${NC}"
        echo -e "${BLUE}执行命令: ${CMD}${NC}"
        nohup bash -c "$CMD" > "$log_file" 2>&1 &
        PID=$!

        ## 保存PID到logs目录下的文件
        echo $PID > ${pid_file}
        echo -e "${GREEN}任务流已在后台启动，PID: ${PID}${NC}"
        echo -e "${BLUE}PID保存至: ${pid_file}${NC}"
        echo -e "${BLUE}要查看日志，请运行: tail -f ${log_file}${NC}"
        echo -e "${BLUE}要终止进程，请运行: $0 stop ${TASK_CONFIG}${NC}"
        ;;
        
    stop)
        # 打印标题
        echo -e "${BLUE}===========================================${NC}"
        echo -e "${RED}TaskFlow进程终止工具${NC}"
        echo -e "${BLUE}===========================================${NC}"

        # 首先检查logs目录下的PID文件是否存在
        if [ -f ${pid_file} ]; then
            PID=$(cat ${pid_file})
            echo -e "${BLUE}找到PID文件: ${pid_file}${NC}"
            
            if ps -p $PID > /dev/null; then
                echo -e "${YELLOW}进程正在运行 (PID: $PID)${NC}"
                echo -e "${RED}正在终止进程...${NC}"
                kill -9 $PID
                rm ${pid_file}
                echo -e "${GREEN}✓ 进程已成功终止${NC}"
                echo -e "${GREEN}✓ 已删除PID文件${NC}"
            else
                echo -e "${YELLOW}PID文件存在，但进程 (PID: $PID) 已不存在${NC}"
                rm ${pid_file}
                echo -e "${GREEN}✓ 已清理PID文件${NC}"
            fi
        else
            echo -e "${YELLOW}未找到PID文件: ${pid_file}${NC}"
            echo -e "${BLUE}尝试查找TaskFlow进程...${NC}"
            
            # 检查是否存在taskflow命令
            if command -v taskflow &> /dev/null; then
                echo -e "${BLUE}检查taskflow命令启动的进程...${NC}"
                TASKFLOW_PID=$(ps aux | grep "[t]askflow.*${config_file}" | grep "$target_dir" | awk '{print $2}')
                
                if [ ! -z "$TASKFLOW_PID" ]; then
                    echo -e "${YELLOW}找到taskflow进程 (PID: $TASKFLOW_PID)${NC}"
                    echo -e "${RED}正在终止进程...${NC}"
                    kill -9 $TASKFLOW_PID
                    echo -e "${GREEN}✓ 进程已成功终止${NC}"
                else
                    echo -e "${YELLOW}未找到使用taskflow命令启动的进程${NC}"
                fi
            fi
            
            # 检查Python脚本启动的进程
            echo -e "${BLUE}检查Python脚本启动的进程...${NC}"
            PYTHON_PID=$(ps aux | grep "[p]ython.*${SCRIPT_NAME}.*${config_file}" | grep "$target_dir" | awk '{print $2}')
            
            if [ ! -z "$PYTHON_PID" ]; then
                echo -e "${YELLOW}找到Python进程 (PID: $PYTHON_PID)${NC}"
                echo -e "${RED}正在终止进程...${NC}"
                kill -9 $PYTHON_PID
                echo -e "${GREEN}✓ 进程已成功终止${NC}"
            else
                echo -e "${YELLOW}未找到使用Python启动的${SCRIPT_NAME}进程${NC}"
            fi
        fi

        # 查找子进程 - 更通用的方法
        echo -e "${BLUE}查找可能的子进程...${NC}"
        # 获取所有Python进程
        CHILD_PROCESSES=$(ps aux | grep "[p]ython" | grep "$target_dir" | grep -v "taskflow\|${SCRIPT_NAME}\|grep" | awk '{print $2}')
        
        if [ ! -z "$CHILD_PROCESSES" ]; then
            echo -e "${YELLOW}发现Python子进程:${NC}"
            ps aux | grep "[p]ython" | grep "$target_dir" | grep -v "taskflow\|${SCRIPT_NAME}\|grep" | awk '{printf "  PID: %s  CMD: %s\n", $2, $11}'
            
            # 终止所有子进程
            for pid in $CHILD_PROCESSES; do
                echo -e "${RED}正在终止子进程 (PID: $pid)...${NC}"
                kill -9 $pid
            done
            echo -e "${GREEN}✓ 所有子进程已终止${NC}"
            
            # 等待进程完全终止
            echo -e "${BLUE}等待${WAIT_TIME}秒确保所有进程完全终止...${NC}"
            sleep $WAIT_TIME
            
            # 再次检查是否有残留进程
            REMAINING=$(ps aux | grep "[p]ython" | grep "$target_dir" | grep -v "taskflow\|${SCRIPT_NAME}\|grep" | wc -l)
            if [ $REMAINING -gt 0 ]; then
                echo -e "${YELLOW}警告: 仍有${REMAINING}个进程未终止，请手动检查${NC}"
            else
                echo -e "${GREEN}✓ 确认所有进程已终止${NC}"
            fi
        else
            echo -e "${GREEN}✓ 未发现Python子进程${NC}"
        fi

        echo -e "${GREEN}✓ 操作完成${NC}"
        echo -e "${BLUE}===========================================${NC}"
        ;;
        
    *)
        echo -e "${RED}错误: 未知操作 ${ACTION}${NC}"
        echo -e "支持的操作: start, stop"
        exit 1
        ;;
esac