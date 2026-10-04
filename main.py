import os
import sys
import subprocess
import typer
from dotenv import load_dotenv, set_key
from pathlib import Path
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.formatted_text import HTML
import questionary

from rich.console import Console
from rich.panel import Panel

# Inicializa o Rich Console para formatações bonitas
console = Console()

# Inicializa o Typer
app = typer.Typer(help="Easy CLI")
env_path = Path(__file__).resolve().parent / ".env"

load_dotenv(env_path)

def get_active_cli():
    return os.getenv("ACTIVE_CLI", "agy")

def get_cli_mode():
    return os.getenv("CLI_MODE", "auto")

def update_env(key, value):
    set_key(str(env_path), key, value)
    os.environ[key] = value

def handle_prompt(text: str):
    text = text.strip()
    if not text:
        return
        
    cli = get_active_cli()
        
    if text.startswith("/cli"):
        console.print(f"[{cli}]", style="bold blue")
        novo_cli = questionary.select(
            "Escolha o CLI que deseja usar:",
            choices=["agy", "claude"]
        ).ask()
        if novo_cli:
            update_env("ACTIVE_CLI", novo_cli)
            console.print(f"✓ CLI alterado para {novo_cli}", style="bold green")

    elif text.startswith("/mode"):
        console.print(f"[{get_cli_mode()}]", style="bold blue")
        novo_mode = questionary.select(
            "Escolha o modo que deseja usar:",
            choices=["auto", "ask"]
        ).ask()
        if novo_mode:
            update_env("CLI_MODE", novo_mode)
            console.print(f"✓ Modo alterado para {novo_mode}", style="bold green")
            
    elif text.startswith("test-test"):
        param = text[len("test-test"):].strip()
        if not param:
            console.print("Forneça o texto para o teste.", style="bold red")
            return
            
        prompt_especial = f"traduza o seguinte texto para o idioma russo (forneça APENAS a tradução em russo e mais nada): {param}"
        try:
            # Mostra o spinner de processamento animado
            with console.status(f"[bold yellow]Pedindo tradução para {cli}...", spinner="earth"):
                result = subprocess.run([cli, "-p", prompt_especial], capture_output=True, text=True, check=True, encoding='utf-8', errors='replace')
                resposta = result.stdout.strip()
                
            # Exibe no console no formato visual bonito
            console.print(Panel(f"é isso aqui:\n\n[bold white]{resposta}[/bold white]", title="🇷🇺 Tradução", border_style="green", padding=(1, 2)))
        except subprocess.CalledProcessError as e:
            console.print(f"[bold red]Erro do CLI:[/bold red] {e.stderr if e.stderr else e.output}")
        except Exception as e:
            console.print(f"[bold red]Erro ao executar:[/bold red] {e}")
            
    else:
        # Prompt livre
        try:
            cli_args = [cli, "-p", text]
            
            # Adiciona parâmetros dependendo do modo
            if get_cli_mode() == "auto":
                if cli == "agy":
                    cli_args.insert(1, "--dangerously-skip-permissions")
                elif cli == "claude":
                    cli_args.insert(1, "-y")
                    
            process = subprocess.Popen(
                cli_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                encoding='utf-8',
                errors='replace'
            )
            
            # Animação de processamento aguardando a primeira letra
            with console.status(f"[bold cyan]Processando via {cli}...", spinner="bouncingBar"):
                first_char = process.stdout.read(1)
                
            if first_char:
                # O spinner some! Pula a linha e inicia o streaming da resposta
                sys.stdout.write("\n")
                sys.stdout.write(first_char)
                sys.stdout.flush()
                
                # Joga o restante do streaming direto na tela
                while True:
                    char = process.stdout.read(1)
                    if not char:
                        break
                    sys.stdout.write(char)
                    sys.stdout.flush()
                
                sys.stdout.write("\n")
                
            process.wait()
            
        except Exception as e:
            console.print(f"[bold red]Erro ao executar o CLI {cli}:[/bold red] {e}")

@app.command()
def repl():
    # Painel de boas vindas
    welcome_text = """[bold white]Comandos disponíveis:[/bold white]
  [cyan]/cli[/cyan]     - Configura qual IA usar (agy/claude)
  [cyan]/mode[/cyan]    - Configura o modo de execução (auto/ask)
  [cyan]test-test[/cyan] - Testa comando traduzindo texto para russo
  [cyan]exit / quit[/cyan] - Sair da ferramenta

[dim]Qualquer outro texto será enviado diretamente para a IA selecionada![/dim]"""

    console.print(
        Panel(
            welcome_text, 
            title="🚀 [bold magenta]Bem vindo ao Easy CLI[/bold magenta]", 
            border_style="magenta",
            padding=(1, 2)
        )
    )
    
    session = PromptSession(history=InMemoryHistory())
    while True:
        try:
            # Prompt bonito pintado via HTML tagging do prompt_toolkit
            cli_prompt = HTML(f"\n<b><ansicyan>easy ({get_active_cli()}|{get_cli_mode()})</ansicyan></b> <ansigreen>❯</ansigreen> ")
            text = session.prompt(cli_prompt)
            
            if text.strip().lower() in ["exit", "quit"]:
                console.print("\n[bold green]Saindo do Easy CLI. Até logo![/bold green]")
                break
                
            handle_prompt(text)
        except (KeyboardInterrupt, EOFError):
            console.print("\n[bold green]Saindo do Easy CLI. Até logo![/bold green]")
            break

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        repl()

if __name__ == "__main__":
    app()
