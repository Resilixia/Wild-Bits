from pathlib import Path
from typing import Union

import botw
import oead
from oead.yaz0 import decompress
from rstb import ResourceSizeTable
import webview
from . import EXEC_DIR, _sarc, _rstb

class Api:
    window: webview.Window
    _open_sarc: oead.Sarc
    _open_rstb: ResourceSizeTable
    _open_rstb_be: bool
    _open_byml: Union[oead.byml.Hash, oead.byml.Array]
    _open_pio: oead.aamp.ParameterIO
    _open_msbt: dict
    
    def browse(self) -> Union[str, None]:
        result = self.window.create_file_dialog(webview.OPEN_DIALOG)
        if result:
            return result[0]
        else:
            return None
    
    ###############
    # SARC Editor #
    ###############
    def open_sarc(self) -> dict:
        result = self.browse()
        if not result:
            return {}
        file = Path(result)
        try:
            self._open_sarc, tree = _sarc.open_sarc(file)
        except ValueError:
            return {}
        return {
            'path': str(file.resolve()),
            'sarc': tree,
            'be': self._open_sarc.get_endianness() == oead.Endianness.Big
        }

    def create_sarc(self, be: bool, alignment: int) -> dict:
        tmp_sarc = oead.SarcWriter(
            oead.Endianness.Big if be else oead.Endianness.Little,
            oead.SarcWriter.Mode.New if alignment == 4 else oead.SarcWriter.Mode.Legacy
        )
        self._open_sarc, tree = _sarc.open_sarc(
            oead.Sarc(
                tmp_sarc.write()[1]
            )
        )
        return {
            'sarc': tree,
            'be': be,
            'path': ''
        }
        
    def save_sarc(self, path: str = '') -> dict:
        if not path:
            result = self.window.create_file_dialog(webview.SAVE_DIALOG)
            if result:
                path = result[0]
            else:
                return {'error': 'Cancelled'}
        path = Path(path)
        try:
            path.write_bytes(
                oead.SarcWriter.from_sarc(self._open_sarc).write()[1]
            )
        except (ValueError, OSError) as e:
            return {'error': str(e)}
        else:
            return {}
        
        
    def get_file_info(self, file: str, wiiu: bool) -> dict:
        return _sarc.get_nested_file_meta(self._open_sarc, file, wiiu)
    
    def extract_sarc_file(self, file: str) -> dict:
        filename = Path(file).name
        output = self.window.create_file_dialog(
            webview.SAVE_DIALOG,
            save_filename=filename
        )
        if output:
            out = Path(output[0])
            try:
                out.write_bytes(
                    _sarc.get_nested_file_data(
                        self._open_sarc, file, unyaz=False
                    )
                )
                return {
                    'success': True
                }
            except Exception as e:
                return {
                    'error': str(e)
                }
    
    def rename_sarc_file(self, file: str, new_name: str) -> dict:
        try:
            self._open_sarc, tree = _sarc.open_sarc(
                _sarc.rename_file(self._open_sarc, file, new_name)
            )
        except (ValueError, KeyError) as e:
            return {'error': str(e)}
        return tree

    def delete_sarc_file(self, file: str) -> dict:
        try:
            self._open_sarc, tree = _sarc.open_sarc(
                _sarc.delete_file(self._open_sarc, file)
            )
        except (ValueError, KeyError) as e:
            return {'error': str(e)}
        return tree
    
    def add_sarc_file(self, file: str, sarc_path: str) -> dict:
        try:
            data = memoryview(Path(file).read_bytes())
            self._open_sarc, tree = _sarc.open_sarc(
                _sarc.add_file(self._open_sarc, sarc_path, data)
            )
        except (AttributeError, ValueError, KeyError, OSError, TypeError, FileNotFoundError) as e:
            return {'error': str(e)}
        return tree

    def update_sarc_folder(self) -> dict:
        result = self.window.create_file_dialog(webview.FOLDER_DIALOG)
        if not result:
            return {}
        try:
            self._open_sarc, tree = _sarc.open_sarc(
                _sarc.update_from_folder(self._open_sarc, Path(result[0]))
            )
        except (FileNotFoundError, OSError, ValueError) as e:
            return {'error': str(e)}
        return tree

    def extract_sarc(self):
        result = self.window.create_file_dialog(webview.FOLDER_DIALOG)
        if not result:
            return {}
        try:
            output = Path(result[0])
            for file in self._open_sarc.get_files():
                (output / file.name).parent.mkdir(parents=True, exist_ok=True)
                (output / file.name).write_bytes(file.data)
        except (FileNotFoundError, OSError) as e:
            return {'error': str(e)}
        return {}

    ###############
    # RSTB Editor #
    ###############
    def open_rstb(self):
        result = self.browse()
        if not result:
            return {}
        file = Path(result)
        try:
            self._open_rstb, self._open_rstb_be = _rstb.open_rstb(file)
        except (ValueError, IndexError) as e:
            return {'error': str(e)}
        return {
            'path': str(file.resolve()),
            'rstb': {
                _rstb.get_name_from_hash(crc): size for crc, size in self._open_rstb.crc32_map.items()
            },
            'be': self._open_rstb_be
        }


def main():
    api = Api()
    api.window = webview.create_window('Wild Bits', url=str(EXEC_DIR / 'assets' / 'index.html'), js_api=api)
    webview.start(
        debug=True,
        http_server=False,
        gui='gtk'
    )


if __name__ == "__main__":
    main()