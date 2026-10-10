"""Compatibilidad: genera avatares vectoriales nítidos y expresiones locales."""
try:
    from .generar_avatares_vectoriales import main
except ImportError:
    from generar_avatares_vectoriales import main

if __name__ == '__main__':
    main()
