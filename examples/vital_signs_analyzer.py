import numpy as np
import matplotlib.pyplot as plt

class VitalSignsAnalyzer:
    """
    生命体征分析器的Python实现,用于分析呼吸率和心率。
    
    该类使用基于FFT的频谱分析来从相位数据中提取呼吸率(BR)和心率(HR)。
    """
    
    def __init__(self):
        """初始化生命体征分析器"""
        pass
    
    def display3s(self, phase, periodicity, display_or_not=True):
        """
        分析相位数据以提取呼吸率和心率。
        
        参数:
            phase (numpy.ndarray): 相位数据数组
            periodicity (float): 用于频率计算的周期性参数
            display_or_not (bool): 是否显示图表
        
        返回:
            tuple: (BR, HR) - 呼吸率和心率(每分钟次数)
        """
        # 创建频率数组
        f = np.arange(1024) / 2048 / periodicity
        
        # 计算FFT
        Y = np.abs(np.fft.fft(phase, 2048, axis=0))
        Y = Y[:1024,:]  # 取前1024个点
        
        # 将前13个点置零(去除直流分量和极低频)
        Y[:13,:] = 0
        
        # 找到最大值并创建修改后的频谱Y2
        x = np.argmax(Y,axis=0)
        BY11 = np.zeros((1024,3))
        BY11[13:69,:] = np.abs(Y[13:69,:])  # 调整为基于0的索引
        
        # 找到呼吸率
        x_br = np.argmax(BY11,axis=0)
        BR = f[x_br] * 60
        
        # 子图3: 心率分析(73-344范围)
        BY21 = np.zeros((1024,3))
        BY21[72:344,:] = np.abs(Y[72:344,:])  # 调整为基于0的索引
        
        # 找到心率
        x_hr = np.argmax(BY21,axis=0)
        HR = f[x_hr] * 60
        
        # 仅在启用显示时创建三个子图
        if display_or_not:
            fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, 6))
            
            # 子图1: 完整频谱
            ax1.plot(f * 60, np.abs(Y), linewidth=1, label='Original')
            ax1.set_title('Breathing Spectrum', fontsize=16)
            ax1.set_xlabel('Beats per minute', fontsize=14)
            ax1.set_ylabel('Magnitude (a.u.)', fontsize=14)
            ax1.grid(True)
            ax1.set_xlim([0, 200])
            ax1.legend(['RX1','RX2','RX3'])
            ax1.tick_params(labelsize=12)
            
            # 以分贝形式绘制呼吸频谱
            BY11_max = np.max(BY11,axis=0)
            BY11_db = 20 * np.log10(np.maximum(BY11, BY11_max * 1e-10) / BY11_max)

            ax2.plot(f * 60, BY11_db, linewidth=1, label='Original')
            ax2.set_title('Breathing Spectrum', fontsize=16)
            ax2.set_xlabel('Beats per minute', fontsize=14)
            ax2.set_ylabel('Magnitude (a.u.)/dB', fontsize=14)
            ax2.grid(True)
            ax2.set_xlim([5, 45])
            ax2.set_ylim([-40, 0])
            ax2.legend(['RX1','RX2','RX3'])
            ax2.tick_params(labelsize=12)
            
            # 以分贝形式绘制心率频谱
            BY21_max = np.max(BY21,axis=0)
            BY21_db = 20 * np.log10(np.maximum(BY21, BY21_max * 1e-10) / BY21_max)
            
            ax3.plot(f * 60, BY21_db, linewidth=1, label='Original')
            ax3.set_title('Heart Rate Spectrum', fontsize=16)
            ax3.set_xlabel('Beats per minute', fontsize=14)
            ax3.set_ylabel('Magnitude (a.u.)/dB', fontsize=14)
            ax3.grid(True)
            ax3.set_xlim([40, 200])
            ax3.set_ylim([-40, 0])
            ax3.legend(['RX1','RX2','RX3'])
            ax3.tick_params(labelsize=12)
            
            plt.tight_layout()
            plt.show()
        
        return BR, HR