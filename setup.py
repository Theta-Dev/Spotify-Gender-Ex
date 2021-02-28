# coding=utf-8
import setuptools

with open('README.md') as f:
    README = f.read()

setuptools.setup(
    name='Spotify-Gender-Ex',
    version='2.0.0',
    author='ThetaDev',
    description='Ein kleines Tool, das die Gendersternchen (z.B. Künstler*innen) aus der Spotify-App für Android entfernt.',
    long_description=README,
    long_description_content_type='text/markdown',
    license='MIT License',
    url="https://github.com/Theta-Dev/Spotify-Gender-Ex",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
    ],
    py_modules=['spotify_gender_ex'],
    install_requires=[
        'click',
        'tqdm',
        'importlib_resources',
        'pyyaml',
        'requests'
    ],
    packages=setuptools.find_packages(exclude=['tests*']),
    package_data={
        'spotify_gender_ex': ['lib/*', 'res/*']
    },
    entry_points={
        'console_scripts': [
            'spotify-gender-ex=spotify_gender_ex:run',
        ],
    },
)
