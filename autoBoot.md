# Faradex Test Service Setup Guide

This guide explains how to set up, manage, and control the Faradex Test Routine Service using systemd.

## Service File Setup

Create or edit the service file:
```bash
sudo nano /etc/systemd/system/faradex-test.service
```

Add the following content to the file:
```ini
[Unit]
Description=Faradex Test Routine Service
After=network.target
StartLimitIntervalSec=300
StartLimitBurst=5

[Service]
Type=simple
Environment="PATH=/home/Faradex/rs485_env/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="VIRTUAL_ENV=/home/Faradex/rs485_env"
WorkingDirectory=/home/Faradex/PythonScripts/TestRoutine_Witty/src
ExecStart=/bin/bash -c 'source /home/Faradex/rs485_env/bin/activate && python3 testRoutine_parallelAlpha.py'
Restart=on-failure
RestartSec=30
User=Faradex
Group=Faradex

[Install]
WantedBy=multi-user.target
```

## Initial Setup

After creating or modifying the service file, run these commands:
```bash
# Reload the systemd configuration
sudo systemctl daemon-reload

# Start the service
sudo systemctl start faradex-test.service

# Enable the service to start at boot
sudo systemctl enable faradex-test.service
```

## Service Management

### Basic Commands

Check service status:
```bash
sudo systemctl status faradex-test.service
```

Stop the service:
```bash
sudo systemctl stop faradex-test.service
```

Start the service:
```bash
sudo systemctl start faradex-test.service
```

Restart the service:
```bash
sudo systemctl restart faradex-test.service
```

### Boot Behavior

Disable service from starting at boot:
```bash
sudo systemctl disable faradex-test.service
```

Enable service to start at boot:
```bash
sudo systemctl enable faradex-test.service
```

## Troubleshooting

### View Service Logs
```bash
# View all logs for the service
journalctl -u faradex-test.service

# View most recent logs
journalctl -u faradex-test.service -n 50

# Follow logs in real-time
journalctl -u faradex-test.service -f
```

### Common Issues

1. **Path Issues**: Ensure all paths in the service file are absolute and correct
2. **Permission Issues**: Verify the Faradex user has necessary permissions
3. **Virtual Environment**: Confirm the rs485_env virtual environment exists and is accessible

## Notes

- The service is configured to restart automatically on failure
- Restart attempts are limited to prevent excessive restarts
- The service runs under the Faradex user account
- The virtual environment is activated before running the Python script