module.exports = {
  apps: [
    {
      name: "ocr-server",
      script: "ocr_server.py",
      interpreter: "pythonw",
      cwd: __dirname,
      watch: false,
      autorestart: true,
      max_restarts: 10,
      restart_delay: 3000,
    },
  ],
};
