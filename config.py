import os
import sys
import subprocess
import shutil
import platform
import ctypes
from pathlib import Path

def require_admin():
    os_name = platform.system()
    if os_name == "Windows":
        try:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
        except Exception:
            is_admin = False
        if not is_admin:
            print("Solicitando privilégios administrativos...")
            # Pega o caminho absoluto para o script, já que o UAC pode mudar o diretório de execução para System32
            script_path = os.path.abspath(sys.argv[0])
            params = " ".join([f'"{script_path}"'] + sys.argv[1:])
            # Re-executa o script atual com elevação de UAC
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
            sys.exit()
    else:
        # Linux / Mac
        if os.geteuid() != 0:
            print("Solicitando privilégios administrativos (sudo)...")
            # Re-executa o script com sudo
            subprocess.check_call(['sudo', sys.executable] + sys.argv)
            sys.exit()

def main():
    require_admin()
    print("Iniciando configuração do ambiente Easy CLI...")
    base_dir = Path(__file__).resolve().parent
    
    # 1. Identificar o Sistema Operacional
    os_name = platform.system()
    print(f"Sistema Operacional detectado: {os_name}")
    
    # 2. Criar env e instalar dependencias do py
    # Utilizando venv nativo para criar o ambiente isolado do Python
    venv_dir = base_dir / "venv"
    if not venv_dir.exists():
        print("Criando ambiente virtual (venv)...")
        subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
    else:
        print("Ambiente virtual já existe.")
        
    print("Instalando dependências...")
    pip_exe = venv_dir / "Scripts" / "pip.exe" if os_name == "Windows" else venv_dir / "bin" / "pip"
    req_file = base_dir / "requirements.txt"
    subprocess.run([str(pip_exe), "install", "-r", str(req_file)], check=True)
    
    # 3. Verificar clientes
    print("\nVerificando clientes CLI disponíveis (agy, claude)...")
    has_agy = shutil.which("agy") is not None
    has_claude = shutil.which("claude") is not None
    
    print(f"- Encontrado 'agy': {has_agy}")
    print(f"- Encontrado 'claude': {has_claude}")
    
    if not has_agy and not has_claude:
        print("Aviso: Nenhum dos clientes (agy, claude) foi encontrado no PATH global.")
        active_client = "agy" # Default fallback
    elif has_agy:
        active_client = "agy"
    else:
        active_client = "claude"
        
    # 4. Criar arquivo .env
    env_file = base_dir / ".env"
    print(f"\nCriando arquivo .env (CLI ativo marcado como: {active_client})...")
    with open(env_file, "w", encoding="utf-8") as f:
        f.write(f"ACTIVE_CLI={active_client}\n")
        f.write(f"ACTIVE_MODE=autonomo\n")
        
    # 5. Registrar alias no sistema operacional
    print("\nRegistrando alias do CLI ('easy')...")
    python_exe = venv_dir / "Scripts" / "python.exe" if os_name == "Windows" else venv_dir / "bin" / "python"
    main_py = base_dir / "main.py"
    
    if os_name == "Windows":
        # 5.1 Registrar no profile do PowerShell
        ps_cmd = "if (!(Test-Path -Path $PROFILE)) { New-Item -ItemType File -Path $PROFILE -Force }; $PROFILE"
        profile_path_result = subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True, text=True)
        if profile_path_result.returncode == 0:
            profile_path = Path(profile_path_result.stdout.strip())
            alias_code = f'\nfunction easy {{ & "{python_exe}" "{main_py}" $args }}\n'
            
            profile_content = profile_path.read_text(encoding="utf-8") if profile_path.exists() else ""
            if "function easy {" not in profile_content:
                with open(profile_path, "a", encoding="utf-8") as f:
                    f.write(alias_code)
                print(f"Alias 'easy' adicionado ao seu PowerShell Profile ({profile_path}).")
            else:
                print("Alias 'easy' já existe no PowerShell Profile.")
        else:
            print("Erro ao tentar configurar perfil do PowerShell.")
            
        # 5.2 Criar um arquivo .cmd para funcionar no Prompt de Comando (CMD) normal
        cmd_path = base_dir / "easy.cmd"
        with open(cmd_path, "w", encoding="utf-8") as f:
            f.write(f'@echo off\n"{python_exe}" "{main_py}" %*\n')
            
        # Adicionar o diretório base ao PATH do usuário do Windows para o .cmd ser global
        import winreg
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment", 0, winreg.KEY_ALL_ACCESS)
            path_val, _ = winreg.QueryValueEx(key, "Path")
            if str(base_dir) not in path_val:
                new_path = path_val.rstrip(';') + ';' + str(base_dir)
                winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, new_path)
                print("-> A pasta do CLI foi adicionada ao PATH do Windows para rodar no CMD.")
                # Tenta notificar o Windows da mudança nas variáveis de ambiente
                ctypes.windll.user32.SendMessageTimeoutW(0xFFFF, 0x001A, 0, "Environment", 0x02, 1000)
            winreg.CloseKey(key)
        except Exception as e:
            print(f"Erro ao adicionar diretório ao PATH do Windows: {e}")
            
        print("\n-> Por favor, FECHE e ABRA seu terminal novamente (tanto PowerShell quanto CMD) para que o comando funcione.")
    else: # Linux/Mac
        alias_code = f'\nalias easy="{python_exe} {main_py}"\n'
        for rc_name in [".bashrc", ".zshrc"]:
            rc_path = Path.home() / rc_name
            if rc_path.exists():
                content = rc_path.read_text(encoding="utf-8")
                if "alias easy=" not in content:
                    with open(rc_path, "a", encoding="utf-8") as f:
                        f.write(alias_code)
                    print(f"Alias 'easy' adicionado ao ~/{rc_name}.")
                else:
                    print(f"Alias 'easy' já existe no ~/{rc_name}.")

    print("\nConfiguração finalizada com sucesso! Seu CLI 'easy' está pronto para uso.")
    input("\nPressione Enter para fechar...")

if __name__ == "__main__":
    main()
