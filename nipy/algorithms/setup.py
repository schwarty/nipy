# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
def configuration(parent_package='',top_path=None):
    from numpy.distutils.misc_util import Configuration
    config = Configuration('algorithms', parent_package, top_path)

    config.add_data_dir('tests')

    config.add_subpackage('registration')
    config.add_subpackage('segmentation')
    config.add_subpackage('statistics')
    config.add_subpackage('diagnostics')
    config.add_subpackage('clustering')

    return config

if __name__ == '__main__':
    from numpy.distutils.core import setup
    setup(**configuration(top_path='').todict())
