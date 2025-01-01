from nicegui import ui

class KnowledgePage:
    def __init__(self, tab: str = 'chat'):
        with ui.column().classes('w-full'):
            with ui.tabs().classes('w-full') as tabs:
                ui.tab('Chat')
                ui.tab('Admin')
            
            with ui.tab_panels(tabs, value=tab).classes('w-full'):
                with ui.tab_panel('Chat'):
                    self.setup_chat_panel()
                
                with ui.tab_panel('Admin'):
                    self.setup_admin_panel()

    def setup_chat_panel(self):
        with ui.column().classes('w-full gap-4 p-4'):
            self.chat_messages = ui.column().classes('w-full gap-2')
            with ui.row().classes('w-full'):
                self.message_input = ui.input('Type your message').classes('flex-grow')
                ui.button('Send', on_click=self.send_message)

    def setup_admin_panel(self):
        with ui.column().classes('w-full gap-4 p-4'):
            ui.label('Knowledge Base Management').classes('text-xl')
            with ui.row().classes('w-full'):
                ui.upload(on_upload=self.handle_upload).props('accept=.pdf,.txt,.doc,.docx')
            self.documents_list = ui.column().classes('w-full gap-2')
            self.load_documents()

    async def send_message(self):
        if self.message_input.value:
            with self.chat_messages:
                ui.chat_message(self.message_input.value, name='User')
                # Add your chat logic here
            self.message_input.value = ''

    def handle_upload(self, e):
        # Add your document upload logic here
        pass

    def load_documents(self):
        # Add your document loading logic here
        pass 