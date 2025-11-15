#!/usr/bin/env python3

import sys
import os

# Добавляем пути для импорта
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'valutatrade_hub'))

from valutatrade_hub.cli.interface import CLIInterface

def main():
    """Главная функция приложения"""
    try:
        cli = CLIInterface()
        
        # Если переданы аргументы командной строки
        if len(sys.argv) > 1:
            cli.run()
        else:
            # Интерактивный режим
            cli.interactive_mode()
            
    except KeyboardInterrupt:
        print("\nПрограмма завершена.")
    except Exception as e:
        print(f"Критическая ошибка: {e}")

if __name__ == "__main__":
    main()
