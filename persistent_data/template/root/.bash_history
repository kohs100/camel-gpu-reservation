nvidia-smi
apt-get update
apt install build-essential gdb git vim wget openssh-server
vim /etc/ssh/sshd_config
exit
nvidia-smi
export DISPLAY=143.248.41.100:0.0
cd /usr/local/NVIDIA-Nsight-Compute-2025.1
ls
./ncu-ui 
./ncu --config-file off --export test_ncu --force-overwrite --graph-profiling graph --set full --nvtx sleep 10
ls
vim test.py
python3 test.py
pip install torch
python test.py 
./ncu --config-file off --export test_ncu --force-overwrite --graph-profiling graph --set full --nvtx  python test.py
ls
python test.py 
exit
lsblk
htop
apt install htop
htop
apt install nvtop
nvtop
exit
