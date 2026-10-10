"""Punto de entrada compatible para regenerar las expresiones vectoriales."""
try:
    from .generar_avatares_vectoriales import main
except ImportError:
    from generar_avatares_vectoriales import main

if __name__ == '__main__':
    main()
