import logging
from colorama import init, Fore, Style

# 创建控制台处理程序并设置日志级别
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)


class ColoredFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': Fore.BLUE,  # 蓝色
        'INFO': Fore.LIGHTBLACK_EX,  # 浅黑色
        'WARNING': Fore.YELLOW,  # 黄色
        'ERROR': Fore.RED,  # 红色
        'CRITICAL': Fore.RED + Style.BRIGHT  # 红色 + 粗体
    }

    def format(self, record):
        log_color = self.COLORS.get(record.levelname, Fore.RESET)
        log_fmt = f"{log_color}[{record.levelname}]: {Style.RESET_ALL} {record.getMessage()}"
        return log_fmt


# 设置格式化器
console_formatter = ColoredFormatter()

# 将格式化器添加到处理程序
console_handler.setFormatter(console_formatter)

if __name__ == '__main__':
    # 创建 logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    # 将处理程序添加到 logger
    logger.addHandler(console_handler)

    # 输出日志消息
    logger.debug("This is a debug message.")
    logger.info("This is an info message.")
    logger.warning("This is a warning message.")
    logger.error("This is an error message.")
    logger.critical("This is a critical message.")
