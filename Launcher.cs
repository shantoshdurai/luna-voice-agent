using System;
using System.Diagnostics;
using System.IO;
using System.Net.Sockets;
using System.Text;
using System.Threading;

namespace JarvisLauncher
{
    static class Program
    {
        const int IpcPort = 49155;

        static bool SignalRunningInstance()
        {
            try
            {
                using (var client = new TcpClient())
                {
                    var result = client.BeginConnect("127.0.0.1", IpcPort, null, null);
                    bool success = result.AsyncWaitHandle.WaitOne(800, true);
                    if (!success || !client.Connected)
                    {
                        return false;
                    }
                    client.EndConnect(result);
                    var stream = client.GetStream();
                    byte[] data = Encoding.UTF8.GetBytes("SHOW_DASHBOARD\n");
                    stream.Write(data, 0, data.Length);
                    stream.Flush();
                    byte[] buffer = new byte[64];
                    stream.ReadTimeout = 800;
                    try
                    {
                        stream.Read(buffer, 0, buffer.Length);
                    }
                    catch { }
                    return true;
                }
            }
            catch
            {
                return false;
            }
        }

        [STAThread]
        static void Main(string[] args)
        {
            string baseDir = AppDomain.CurrentDomain.BaseDirectory.TrimEnd('\\', '/');

            // 1. If Jarvis is already running: signal it to bring up the dashboard GUI
            if (SignalRunningInstance())
            {
                return;
            }

            // 2. Otherwise: 1st launch starts Jarvis silently in the background
            string bat = Path.Combine(baseDir, "fast_jarvis.bat");
            if (File.Exists(bat))
            {
                try
                {
                    Process.Start(new ProcessStartInfo
                    {
                        FileName = "cmd.exe",
                        Arguments = "/c \"" + bat + "\"",
                        WorkingDirectory = baseDir,
                        CreateNoWindow = true,
                        WindowStyle = ProcessWindowStyle.Hidden,
                        UseShellExecute = false
                    });
                    return;
                }
                catch { }
            }

            string pythonw = Path.Combine(baseDir, @"venv\Scripts\pythonw.exe");
            try
            {
                Process.Start(new ProcessStartInfo
                {
                    FileName = File.Exists(pythonw) ? pythonw : "pythonw.exe",
                    Arguments = "fast_agent.py",
                    WorkingDirectory = baseDir,
                    CreateNoWindow = true,
                    WindowStyle = ProcessWindowStyle.Hidden,
                    UseShellExecute = false
                });
            }
            catch { }
        }
    }
}
