import setuptools

with open('requirements.txt') as f:
    REQUIRES = f.read().splitlines()

setuptools.setup(
    name='Spotify-Gender-Ex',
    version='0.1.0',
    author='ThetaDev',
    description='Ein kleines Tool, das die Gendersternchen (z.B. Künstler*innen) aus der Spotify-App für Android entfernt.',
    license='MIT License',
    py_modules=['main'],
    install_requires=REQUIRES,
    packages=setuptools.find_packages(exclude=['tests*']),
    package_data={
        'spotify_gender_ex': ['lib/*', 'res/*']
    },
    entry_points={
        'console_scripts': [
            'spotify-gender-ex=main:run',
        ],
    },
)
