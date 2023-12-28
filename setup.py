import setuptools

setuptools.setup(
    name="wine_cellar",
    use_scm_version=True,
    author="RJJ",
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    python_requires=">=3.10",
    setup_requires=['setuptools_scm'],
    install_requires=[
        "fastapi<0.100.0",
        "pandas",
        "pydantic<2.0.0",
        "uvicorn",
        "gunicorn",
        "python-dotenv",
        "python-jose[cryptography]",
        "passlib[bcrypt]",
        "python-multipart",
        "fastapi-pagination==0.12.4",
        "loguru"
    ],
    package_data={'': ['*.sql']},
    include_package_data=True
)