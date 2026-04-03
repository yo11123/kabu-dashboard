"""
日本株アプリ v1.2 インストーラー
デスクトップにショートカットを作成し、アプリを開く。
"""
import os
import sys
import shutil
import subprocess
import ctypes

APP_NAME = "日本株アプリ v1.2"
APP_URL = "https://kabu-dashboard-dmmtcx6xgmbuaryhbqjwf8.streamlit.app"


def get_resource_path(filename):
    """PyInstaller でバンドルされたリソースのパスを取得する。"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, filename)
    return os.path.join(os.path.dirname(__file__), filename)


def find_chrome():
    """Chrome の実行パスを探す。"""
    candidates = [
        os.path.join(os.environ.get("PROGRAMFILES", ""), "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(os.environ.get("PROGRAMFILES(X86)", ""), "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google", "Chrome", "Application", "chrome.exe"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def find_edge():
    """Edge の実行パスを探す。"""
    candidates = [
        os.path.join(os.environ.get("PROGRAMFILES(X86)", ""), "Microsoft", "Edge", "Application", "msedge.exe"),
        os.path.join(os.environ.get("PROGRAMFILES", ""), "Microsoft", "Edge", "Application", "msedge.exe"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def create_shortcut(browser_path, icon_path):
    """デスクトップにショートカットを作成する。"""
    try:
        import win32com.client
        shell = win32com.client.Dispatch("WScript.Shell")
        desktop = shell.SpecialFolders("Desktop")
        shortcut_path = os.path.join(desktop, f"{APP_NAME}.lnk")
        shortcut = shell.CreateShortcut(shortcut_path)
        shortcut.TargetPath = browser_path
        shortcut.Arguments = f"--app={APP_URL}"
        shortcut.WorkingDirectory = os.path.dirname(browser_path)
        shortcut.IconLocation = f"{icon_path},0"
        shortcut.Description = APP_NAME
        shortcut.Save()
        return shortcut_path
    except ImportError:
        # win32com がない場合は PowerShell で作成
        desktop = os.path.join(os.environ["USERPROFILE"], "Desktop")
        shortcut_path = os.path.join(desktop, f"{APP_NAME}.lnk")
        ps_cmd = f'''
$shell = New-Object -ComObject WScript.Shell
$s = $shell.CreateShortcut("{shortcut_path}")
$s.TargetPath = "{browser_path}"
$s.Arguments = "--app={APP_URL}"
$s.IconLocation = "{icon_path},0"
$s.Save()
'''
        subprocess.run(["powershell", "-Command", ps_cmd],
                       capture_output=True, creationflags=0x08000000)
        return shortcut_path


def install_icon():
    """アイコンファイルをアプリデータにコピーする。"""
    app_dir = os.path.join(os.environ.get("LOCALAPPDATA", ""), "KabuDashboard")
    os.makedirs(app_dir, exist_ok=True)
    src = get_resource_path("kabu-dashboard.ico")
    dst = os.path.join(app_dir, "kabu-dashboard.ico")
    if os.path.exists(src):
        shutil.copy2(src, dst)
    return dst


def main():
    # ブラウザを探す
    browser = find_chrome() or find_edge()
    if not browser:
        ctypes.windll.user32.MessageBoxW(
            0,
            "Google Chrome または Microsoft Edge が見つかりません。\nインストールしてから再実行してください。",
            APP_NAME,
            0x10  # MB_ICONERROR
        )
        sys.exit(1)

    browser_name = "Chrome" if "chrome" in browser.lower() else "Edge"

    # アイコンをインストール
    icon_path = install_icon()

    # ショートカット作成
    shortcut_path = create_shortcut(browser, icon_path)

    # 完了メッセージ
    ctypes.windll.user32.MessageBoxW(
        0,
        f"✅ インストール完了！\n\n"
        f"デスクトップに「{APP_NAME}」のショートカットを作成しました。\n"
        f"（{browser_name} で開きます）\n\n"
        f"アプリを起動しますか？",
        f"{APP_NAME} セットアップ",
        0x24  # MB_ICONQUESTION | MB_YESNO
    )

    # アプリを起動
    subprocess.Popen([browser, f"--app={APP_URL}"])


if __name__ == "__main__":
    main()
