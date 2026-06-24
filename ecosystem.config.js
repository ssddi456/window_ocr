module.exports = {
  apps: [
    {
      name: "window-ocr-server",
      script: "server.exe",
      cwd: "./server-go",
      args: "",
      interpreter: "none",
      env: {
        NODE_ENV: "production",
      },
      log_date_format: "YYYY-MM-DD HH:mm:ss",
      error_file: "logs/error.log",
      out_file: "logs/out.log",
      merge_logs: true,
      autorestart: true,
      max_restarts: 10,
      restart_delay: 3000,
    },
  ],
};