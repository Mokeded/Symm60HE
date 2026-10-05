/*
 * This program is free software: you can redistribute it and/or modify it under
 * the terms of the GNU General Public License as published by the Free Software
 * Foundation, either version 3 of the License, or (at your option) any later
 * version.
 *
 * This program is distributed in the hope that it will be useful, but WITHOUT
 * ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
 * FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
 * details.
 *
 * You should have received a copy of the GNU General Public License along with
 * this program. If not, see <https://www.gnu.org/licenses/>.
 */

import { ResizableHandle as Handle } from "../ui/resizable"
import Container from "./keyboard-editor-container.svelte"
import Keyboard from "./keyboard-editor-keyboard.svelte"
import LayoutDialog from "./keyboard-editor-layout-dialog.svelte"
import Menubar from "./keyboard-editor-menubar.svelte"
import Pane from "./keyboard-editor-pane.svelte"
import Root from "./keyboard-editor.svelte"

export {
  Root,
  Pane,
  Container,
  Handle,
  Keyboard,
  Menubar,
  LayoutDialog,
  //
  Root as KeyboardEditor,
  Pane as KeyboardEditorPane,
  Container as KeyboardEditorContainer,
  Handle as KeyboardEditorHandle,
  Keyboard as KeyboardEditorKeyboard,
  Menubar as KeyboardEditorMenubar,
  LayoutDialog as KeyboardEditorLayoutDialog,
}
