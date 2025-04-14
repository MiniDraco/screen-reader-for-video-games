:: Screen Reader Installer @echo off setlocal EnableDelayedExpansion

:: Check for admin rights net session &gt;nul 2&gt;&1 if %errorlevel% neq 0 ( echo This script requires administrative privileges. echo Please run as administrator. pause exit /b 1 )

:: Define installation paths set "INSTALL_DIR=%ProgramFiles%\\ScreenReader" set "BIN_DIR=%INSTALL_DIR%\\bin" set "TESS_DIR=%BIN_DIR%\\tesseract" set "PYTHON_URL=https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe" set "TESS_URL=https://github.com/UB-Mannheim/tesseract/releases/download/v5.4.0.20240606/tesseract-ocr-w64-setup-5.4.0.20240606.exe"

:: Create installation directory echo Creating installation directory... mkdir "%INSTALL_DIR%" 2&gt;nul mkdir "%BIN_DIR%" 2&gt;nul mkdir "%TESS_DIR%" 2&gt;nul

:: Download Python echo Downloading Python 3.11.9... curl -L -o "%TEMP%\\python-installer.exe" "%PYTHON_URL%" if %errorlevel% neq 0 ( echo Failed to download Python. pause exit /b 1 )

:: Install Python silently echo Installing Python... start /wait "" "%TEMP%\\python-installer.exe" /quiet InstallAllUsers=1 PrependPath=1 if %errorlevel% neq 0 ( echo Python installation failed. pause exit /b 1 ) del "%TEMP%\\python-installer.exe"

:: Verify Python python --version &gt;nul 2&gt;&1 if %errorlevel% neq 0 ( echo Python not found after installation. pause exit /b 1 )

:: Upgrade pip echo Upgrading pip... python -m pip install --upgrade pip if %errorlevel% neq 0 ( echo Failed to upgrade pip. pause exit /b 1 )

:: Install wheel to ensure binary distributions echo Installing wheel... pip install wheel if %errorlevel% neq 0 ( echo Failed to install wheel. pause exit /b 1 )

:: Install Python dependencies echo Installing Python dependencies... pip install pyttsx3==2.90 googletrans==3.1.0a0 pytesseract==0.3.10 pillow==10.4.0 keyboard==0.13.5 pydub==0.31.0 if %errorlevel% neq 0 ( echo Failed to install Python dependencies (excluding pygame). pause exit /b 1 )

:: Install pygame with prebuilt wheel echo Installing pygame... pip install pygame==2.6.0 --no-build-isolation --no-deps if %errorlevel% neq 0 ( echo Failed to install pygame. Trying to install build tools... curl -L -o "%TEMP%\\vs_buildtools.exe" "https://aka.ms/vs/17/release/vs_buildtools.exe" start /wait "" "%TEMP%\\vs_buildtools.exe" --quiet --wait --norestart --add Microsoft.VisualStudio.Component.VC.Tools.x86.x64 del "%TEMP%\\vs_buildtools.exe" pip install pygame==2.6.0 if %errorlevel% neq 0 ( echo Failed to install pygame even after build tools. pause exit /b 1 ) )

:: Download Tesseract echo Downloading Tesseract-OCR... curl -L -o "%TEMP%\\tesseract-installer.exe" "%TESS_URL%" if %errorlevel% neq 0 ( echo Failed to download Tesseract. pause exit /b 1 )

:: Install Tesseract silently echo Installing Tesseract-OCR... start /wait "" "%TEMP%\\tesseract-installer.exe" /S /D="%TESS_DIR%" if %errorlevel% neq 0 ( echo Tesseract installation failed. pause exit /b 1 ) del "%TEMP%\\tesseract-installer.exe"

:: Download Tesseract language data echo Downloading Tesseract language data... curl -L -o "%TESS_DIR%\\tessdata\\eng.traineddata" "https://github.com/tesseract-ocr/tessdata_best/raw/main/eng.traineddata" if %errorlevel% neq 0 ( echo Failed to download Tesseract language data. pause exit /b 1 )

:: Copy screen reader script echo Copying screen reader script... copy "%\~dp0screenreader.py" "%BIN_DIR%\\screenreader.py" if %errorlevel% neq 0 ( echo Failed to copy screen reader script. pause exit /b 1 )

:: Create launcher script echo Creating launcher... ( echo @echo off echo python "%BIN_DIR%\\screenreader.py" %%\* ) &gt; "%BIN_DIR%\\screenreader.bat" if %errorlevel% neq 0 ( echo Failed to create launcher. pause exit /b 1 )

:: Add to PATH echo Updating system PATH... set "NEW_PATH=%BIN_DIR%" for /f "tokens=2\*" %%A in ('reg query "HKLM\\SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Environment" /v Path') do set "OLD_PATH=%%B" if defined OLD_PATH ( set "NEW_PATH=%OLD_PATH%;%NEW_PATH%" ) reg add "HKLM\\SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Environment" /v Path /t REG_EXPAND_SZ /d "%NEW_PATH%" /f if %errorlevel% neq 0 ( echo Failed to update PATH. pause exit /b 1 )

:: Create desktop shortcut echo Creating desktop shortcut... echo Set oWS = WScript.CreateObject("WScript.Shell") &gt; "%TEMP%\\shortcut.vbs" echo Set oLink = oWS.CreateShortcut("%USERPROFILE%\\Desktop\\ScreenReader.lnk") &gt;&gt; "%TEMP%\\shortcut.vbs" echo oLink.TargetPath = "%BIN_DIR%\\screenreader.bat" &gt;&gt; "%TEMP%\\shortcut.vbs" echo oLink.WorkingDirectory = "%BIN_DIR%" &gt;&gt; "%TEMP%\\shortcut.vbs" echo oLink.Save &gt;&gt; "%TEMP%\\shortcut.vbs" cscript //nologo "%TEMP%\\shortcut.vbs" del "%TEMP%\\shortcut.vbs"

:: Configure Tesseract path echo Configuring Tesseract... setx TESSERACT_PATH "%TESS_DIR%\\tesseract.exe" if %errorlevel% neq 0 ( echo Failed to set Tesseract path. pause exit /b 1 )

echo Installation complete! You can run 'screenreader' from CMD or use the desktop shortcut. pause exit /b 0