import tkinter as tk
from tkinter import messagebox, ttk
import json
from datetime import datetime
import re 

# --- Classes de Modelo (Produto, ItemPedido, Pedido, Cliente, Lanchonete) ---

class Produto:
    def __init__(self, id_produto: str, nome: str, preco: float, disponivel: bool = True, estoque: int = 0):
        self.id_produto = id_produto
        self.nome = nome
        self.preco = preco
        self.disponivel = disponivel
        self.estoque = estoque

    def __str__(self):
        status = "Disponível" if self.disponivel else "Indisponível"
        return f"Produto: {self.nome} (ID: {self.id_produto}) - R${self.preco:.2f} - Estoque: {self.estoque} - Status: {status}"

    def atualizar_disponibilidade(self, disponivel: bool):
        self.disponivel = disponivel

    def atualizar_info(self, nome: str = None, preco: float = None, estoque: int = None):
        if nome:
            self.nome = nome
        if preco is not None:
            self.preco = preco
        if estoque is not None:
            self.estoque = estoque
        return True

    def to_dict(self):
        return {
            "id_produto": self.id_produto,
            "nome": self.nome,
            "preco": self.preco,
            "disponivel": self.disponivel,
            "estoque": self.estoque
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(data["id_produto"], data["nome"], data["preco"], data["disponivel"], data.get("estoque", 0))

class ItemPedido:
    def __init__(self, produto: Produto, quantidade: int):
        if quantidade <= 0:
            raise ValueError("A quantidade do item deve ser maior que zero.")
        self.produto = produto
        self.quantidade = quantidade
        self.subtotal = produto.preco * quantidade

    def __str__(self):
        return f"{self.produto.nome} (x{self.quantidade}) - R${self.subtotal:.2f}"

    def to_dict(self):
        return {
            "produto_id": self.produto.id_produto,
            "quantidade": self.quantidade,
            "subtotal": self.subtotal
        }

    @classmethod
    def from_dict(cls, data: dict, cardapio_ref: dict):
        produto = cardapio_ref.get(data["produto_id"])
        if not produto:
            raise ValueError(f"Produto com ID {data['produto_id']} não encontrado no cardápio durante carregamento do pedido.")
        return cls(produto, data["quantidade"])

class Pedido:
    _id_counter = 0

    def __init__(self, id_cliente: str, id_pedido: str = None, status: str = "Pendente",
                 data_hora_criacao: datetime = None, valor_total: float = 0.0):
        if id_pedido:
            self.id_pedido = id_pedido
            numeric_id = int(id_pedido[3:])
            if numeric_id >= Pedido._id_counter:
                Pedido._id_counter = numeric_id
        else:
            Pedido._id_counter += 1
            self.id_pedido = f"PED{Pedido._id_counter:04d}"

        self.id_cliente = id_cliente
        self.itens = []
        self.status = status
        self.data_hora_criacao = data_hora_criacao if data_hora_criacao else datetime.now()
        self.valor_total = valor_total

    def adicionar_item(self, produto: Produto, quantidade: int):
        if not produto.disponivel:
            return False, f"Produto '{produto.nome}' não está disponível."
        
        # O estoque é verificado pelo PDV antes de adicionar. Aqui, assumimos que está ok.
        if produto.estoque < quantidade:
            return False, f"Estoque insuficiente para '{produto.nome}'. Disponível: {produto.estoque}"

        for item in self.itens:
            if item.produto.id_produto == produto.id_produto:
                if produto.estoque < (item.quantidade + quantidade):
                    return False, f"Adicionar mais '{produto.nome}' excede o estoque. Disponível: {produto.estoque}"
                
                self.valor_total -= item.subtotal
                item.quantidade += quantidade
                item.subtotal = item.produto.preco * item.quantidade
                self.valor_total += item.subtotal
                return True, ""
        
        item = ItemPedido(produto, quantidade)
        self.itens.append(item)
        self.valor_total += item.subtotal
        return True, ""

    def remover_item(self, id_produto: str):
        item_removido = None
        for item in self.itens:
            if item.produto.id_produto == id_produto:
                self.itens.remove(item)
                self.valor_total -= item.subtotal
                item_removido = item
                break
        return True if item_removido else False

    def atualizar_status(self, novo_status: str):
        status_validos = ["Pendente", "Em Preparo", "Pronto", "Entregue", "Cancelado"]
        if novo_status in status_validos:
            self.status = novo_status
            return True
        return False

    def to_dict(self):
        return {
            "id_pedido": self.id_pedido,
            "id_cliente": self.id_cliente,
            "itens": [item.to_dict() for item in self.itens],
            "status": self.status,
            "data_hora_criacao": self.data_hora_criacao.isoformat(),
            "valor_total": self.valor_total
        }

    @classmethod
    def from_dict(cls, data: dict, cardapio_ref: dict):
        pedido = cls(
            id_cliente=data["id_cliente"],
            id_pedido=data["id_pedido"],
            status=data["status"],
            data_hora_criacao=datetime.fromisoformat(data["data_hora_criacao"]),
            valor_total=data["valor_total"]
        )
        for item_data in data["itens"]:
            produto = cardapio_ref.get(item_data["produto_id"])
            if produto:
                pedido.itens.append(ItemPedido(produto, item_data["quantidade"]))
            else:
                print(f"Aviso: Produto com ID {item_data['produto_id']} não encontrado no cardápio durante carregamento do pedido.")
        return pedido

class Cliente:
    def __init__(self, id_cliente: str, nome: str, telefone: str, endereco: str = None):
        self.id_cliente = id_cliente
        self.nome = nome
        self.telefone = telefone
        self.endereco = endereco

    def __str__(self):
        return f"Cliente: {self.nome} (ID: {self.id_cliente}) - Tel: {self.telefone}"

    def atualizar_info(self, nome: str = None, telefone: str = None, endereco: str = None):
        if nome:
            self.nome = nome
        if telefone:
            self.telefone = telefone
        if endereco:
            self.endereco = endereco
        return True

    def to_dict(self):
        return {
            "id_cliente": self.id_cliente,
            "nome": self.nome,
            "telefone": self.telefone,
            "endereco": self.endereco
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(data["id_cliente"], data["nome"], data["telefone"], data["endereco"])

class Lanchonete:
    def __init__(self, nome: str):
        self.nome = nome
        self.cardapio = {}
        self.clientes = {}
        self.pedidos = {}
        self.ARQUIVO_DADOS = "lanchonete_dados.json"
        self.carregar_dados()

    # --- Validações ---
    def _validar_id(self, id_str: str) -> bool:
        return bool(re.fullmatch(r'^[a-zA-Z0-9]+$', id_str))

    def _validar_telefone(self, tel_str: str) -> bool:
        return bool(re.fullmatch(r'^\d{8,15}$', tel_str))

    # --- Métodos de Produto ---
    def adicionar_produto(self, produto: Produto):
        if not self._validar_id(produto.id_produto):
            return False, "Erro: ID do produto inválido. Use apenas caracteres alfanuméricos."
        if produto.id_produto in self.cardapio:
            return False, f"Erro: Produto com ID '{produto.id_produto}' já existe no cardápio."
        if produto.preco <= 0:
            return False, "Erro: Preço do produto deve ser maior que zero."
        if produto.estoque < 0:
            return False, "Erro: Estoque inicial não pode ser negativo."

        self.cardapio[produto.id_produto] = produto
        self.salvar_dados()
        return True, f"Produto '{produto.nome}' adicionado ao cardápio."

    def remover_produto(self, id_produto: str):
        if id_produto in self.cardapio:
            produto_removido = self.cardapio.pop(id_produto)
            self.salvar_dados()
            return True, f"Produto '{produto_removido.nome}' removido do cardápio."
        return False, f"Erro: Produto com ID '{id_produto}' não encontrado no cardápio."

    def atualizar_produto_info(self, id_produto: str, nome: str = None, preco: float = None, estoque: int = None) -> tuple[bool, str]:
        produto = self.cardapio.get(id_produto)
        if produto:
            if nome is not None and not nome.strip():
                return False, "Erro: Nome do produto não pode ser vazio."
            if preco is not None and preco <= 0:
                return False, "Erro: Preço deve ser maior que zero."
            if estoque is not None and estoque < 0:
                return False, "Erro: Estoque não pode ser negativo."
            
            produto.atualizar_info(nome, preco, estoque)
            self.salvar_dados()
            return True, f"Informações do produto '{produto.id_produto}' atualizadas."
        return False, f"Erro: Produto com ID '{id_produto}' não encontrado."

    def atualizar_disponibilidade_produto(self, id_produto: str, disponivel: bool):
        produto = self.cardapio.get(id_produto)
        if produto:
            produto.atualizar_disponibilidade(disponivel)
            self.salvar_dados()
            return True, f"Disponibilidade de '{produto.nome}' atualizada para: {disponivel}"
        return False, f"Erro: Produto com ID '{id_produto}' não encontrado."

    def exibir_cardapio(self):
        if not self.cardapio:
            return "Cardápio vazio."
        return "\n".join([str(p) for p in self.cardapio.values()])

    # --- Métodos de Cliente ---
    def cadastrar_cliente(self, cliente: Cliente):
        if not self._validar_id(cliente.id_cliente):
            return False, "Erro: ID do cliente inválido. Use apenas caracteres alfanuméricos."
        if cliente.id_cliente in self.clientes:
            return False, f"Erro: Cliente com ID '{cliente.id_cliente}' já cadastrado."
        if not cliente.nome.strip():
            return False, "Erro: Nome do cliente não pode ser vazio."
        if not self._validar_telefone(cliente.telefone):
            return False, "Erro: Telefone inválido. Use apenas dígitos (8 a 15 caracteres)."

        self.clientes[cliente.id_cliente] = cliente
        self.salvar_dados()
        return True, f"Cliente '{cliente.nome}' cadastrado com sucesso."

    def buscar_cliente(self, id_cliente: str):
        return self.clientes.get(id_cliente)

    def atualizar_info_cliente(self, id_cliente: str, nome: str = None, telefone: str = None, endereco: str = None):
        cliente = self.buscar_cliente(id_cliente)
        if cliente:
            if nome is not None and not nome.strip():
                return False, "Erro: Nome do cliente não pode ser vazio."
            if telefone is not None and not self._validar_telefone(telefone):
                return False, "Erro: Telefone inválido. Use apenas dígitos (8 a 15 caracteres)."

            cliente.atualizar_info(nome, telefone, endereco)
            self.salvar_dados()
            return True, f"Informações do cliente '{cliente.nome}' atualizadas."
        return False, f"Erro: Cliente com ID '{id_cliente}' não encontrado."

    def listar_clientes(self):
        if not self.clientes:
            return "Nenhum cliente cadastrado."
        return "\n".join([str(c) for c in self.clientes.values()])

    # --- Métodos de Pedido ---
    def criar_pedido(self, id_cliente: str) -> tuple[bool, str, Pedido | None]:
        if id_cliente not in self.clientes:
            return False, f"Erro: Cliente com ID '{id_cliente}' não encontrado.", None
        novo_pedido = Pedido(id_cliente)
        self.pedidos[novo_pedido.id_pedido] = novo_pedido
        self.salvar_dados()
        return True, f"Pedido {novo_pedido.id_pedido} criado para o cliente '{self.clientes[id_cliente].nome}'.", novo_pedido

    def adicionar_item_a_pedido(self, id_pedido: str, id_produto: str, quantidade: int) -> tuple[bool, str]:
        pedido = self.pedidos.get(id_pedido)
        if not pedido:
            return False, f"Erro: Pedido com ID '{id_pedido}' não encontrado."
        produto = self.cardapio.get(id_produto)
        if not produto:
            return False, f"Erro: Produto com ID '{id_produto}' não encontrado no cardápio."
        
        if quantidade <= 0:
            return False, "Erro: Quantidade do item deve ser maior que zero."

        success, message = pedido.adicionar_item(produto, quantidade)
        if success:
            self.salvar_dados()
            return True, f"Item '{produto.nome}' (x{quantidade}) adicionado ao pedido {id_pedido}."
        else:
            return False, message

    def remover_item_de_pedido(self, id_pedido: str, id_produto: str) -> tuple[bool, str]:
        pedido = self.pedidos.get(id_pedido)
        if not pedido:
            return False, f"Erro: Pedido com ID '{id_pedido}' não encontrado."
        if pedido.remover_item(id_produto):
            self.salvar_dados()
            return True, f"Item '{id_produto}' removido do pedido {id_pedido}."
        return False, f"Produto com ID '{id_produto}' não encontrado no pedido {id_pedido}."

    def atualizar_status_pedido(self, id_pedido: str, novo_status: str) -> tuple[bool, str]:
        pedido = self.pedidos.get(id_pedido)
        if not pedido:
            return False, f"Erro: Pedido com ID '{id_pedido}' não encontrado."
        
        if novo_status == "Entregue" and pedido.status != "Entregue":
            for item in pedido.itens:
                produto = self.cardapio.get(item.produto.id_produto)
                if produto:
                    if produto.estoque < item.quantidade:
                        return False, f"Erro: Estoque insuficiente de '{produto.nome}' para finalizar pedido. Restam {produto.estoque}, pedido requer {item.quantidade}."
                    produto.estoque -= item.quantidade
                else:
                    return False, f"Erro: Produto '{item.produto.id_produto}' não encontrado no cardápio para dedução de estoque."
            self.salvar_dados()
        
        if pedido.atualizar_status(novo_status):
            self.salvar_dados()
            return True, f"Status do pedido {id_pedido} atualizado para '{novo_status}'."
        return False, f"Erro ao atualizar status: Status '{novo_status}' inválido."

    def buscar_pedido(self, id_pedido: str):
        return self.pedidos.get(id_pedido)

    # --- Métodos de Relatório ---
    def relatorio_total_vendas_por_periodo(self, data_inicio: datetime = None, data_fim: datetime = None) -> float:
        total = 0.0
        for pedido in self.pedidos.values():
            if pedido.status == "Entregue":
                if data_inicio and pedido.data_hora_criacao < data_inicio:
                    continue
                if data_fim and pedido.data_hora_criacao > data_fim:
                    continue
                total += pedido.valor_total
        return total

    def relatorio_produtos_mais_vendidos(self, top_n: int = 5) -> list[tuple[str, int]]:
        vendas_por_produto = {}
        for pedido in self.pedidos.values():
            if pedido.status == "Entregue":
                for item in pedido.itens:
                    vendas_por_produto[item.produto.nome] = vendas_por_produto.get(item.produto.nome, 0) + item.quantidade
        
        sorted_products = sorted(vendas_por_produto.items(), key=lambda item: item[1], reverse=True)
        return sorted_products[:top_n]

    def relatorio_pedidos_por_cliente(self, id_cliente: str) -> list[Pedido]:
        cliente = self.clientes.get(id_cliente)
        if not cliente:
            return []
        
        pedidos_do_cliente = [pedido for pedido in self.pedidos.values() if pedido.id_cliente == id_cliente]
        return sorted(pedidos_do_cliente, key=lambda p: p.data_hora_criacao, reverse=True)

    def salvar_dados(self):
        dados = {
            "cardapio": [p.to_dict() for p in self.cardapio.values()],
            "clientes": [c.to_dict() for c in self.clientes.values()],
            "pedidos": [p.to_dict() for p in self.pedidos.values()],
            "next_pedido_id": Pedido._id_counter
        }
        try:
            with open(self.ARQUIVO_DADOS, 'w', encoding='utf-8') as f:
                json.dump(dados, f, indent=4, ensure_ascii=False)
        except IOError as e:
            messagebox.showerror("Erro de Salvar", f"Erro ao salvar dados: {e}")
        except Exception as e:
            messagebox.showerror("Erro Inesperado", f"Ocorreu um erro inesperado ao salvar: {e}")

    def carregar_dados(self):
        try:
            with open(self.ARQUIVO_DADOS, 'r', encoding='utf-8') as f:
                dados = json.load(f)

            self.cardapio = {p["id_produto"]: Produto.from_dict(p) for p in dados.get("cardapio", [])}
            self.clientes = {c["id_cliente"]: Cliente.from_dict(c) for c in dados.get("clientes", [])}
            
            self.pedidos = {}
            for p_data in dados.get("pedidos", []):
                try:
                    temp_pedido_itens = []
                    for item_data in p_data.get("itens", []):
                        produto_id = item_data["produto_id"]
                        if produto_id in self.cardapio:
                            temp_pedido_itens.append(ItemPedido(self.cardapio[produto_id], item_data["quantidade"]))
                        else:
                            print(f"Aviso: Produto '{produto_id}' do pedido '{p_data['id_pedido']}' não encontrado no cardápio durante carregamento. Item ignorado.")
                    
                    pedido = Pedido(
                        id_cliente=p_data["id_cliente"],
                        id_pedido=p_data["id_pedido"],
                        status=p_data["status"],
                        data_hora_criacao=datetime.fromisoformat(p_data["data_hora_criacao"]),
                        valor_total=p_data["valor_total"]
                    )
                    pedido.itens = temp_pedido_itens
                    self.pedidos[pedido.id_pedido] = pedido

                except ValueError as e:
                    print(f"Erro ao carregar pedido {p_data.get('id_pedido')}: {e}. Pedido ignorado.")

            Pedido._id_counter = dados.get("next_pedido_id", 0)

        except FileNotFoundError:
            messagebox.showinfo("Dados", f"Arquivo '{self.ARQUIVO_DADOS}' não encontrado. Iniciando com dados vazios.")
        except json.JSONDecodeError as e:
            messagebox.showerror("Erro de Carregamento", f"Erro ao decodificar JSON do arquivo '{self.ARQUIVO_DADOS}': {e}. Verifique a integridade do arquivo.")
        except Exception as e:
            messagebox.showerror("Erro Inesperado", f"Ocorreu um erro inesperado ao carregar os dados: {e}")


# --- Interface Gráfica com Tkinter ---
class LanchoneteApp:
    def __init__(self, master):
        self.master = master
        master.title("Sistema de Gerenciamento de Lanchonetes")
        master.geometry("1100x780") 
        master.resizable(False, False)

        self.lanchonete = Lanchonete("Minha Lanchonete Deliciosa")

        # As variáveis de cor devem ser atributos da instância para serem acessíveis por outros métodos
        self.BACKGROUND_COLOR = '#F0F0F0' # Light gray
        self.PRIMARY_COLOR = '#4CAF50'    # Green (for primary actions)
        self.ACCENT_COLOR = '#FFC107'     # Amber (for warnings/highlights)
        self.TEXT_COLOR = '#333333'       # Dark gray
        self.HEADER_COLOR = '#2196F3'     # Blue (for headers/frames)
        self.ERROR_COLOR = '#F44336'      # Red

        self.setup_styles()

        self.notebook = ttk.Notebook(master)
        self.notebook.pack(expand=True, fill="both", padx=10, pady=10)

        # Aba de Vendas (PDV) - Prioridade visual
        self.frame_vendas = ttk.Frame(self.notebook, style='Card.TFrame')
        self.notebook.add(self.frame_vendas, text="🛒 Vendas (PDV)")
        
        # Inicialize carrinho_pdv AQUI, antes de chamar criar_interface_vendas
        self.carrinho_pdv = {} # <--- Adicione esta linha

        self.criar_interface_vendas(self.frame_vendas)

        # Outras abas
        self.frame_produtos = ttk.Frame(self.notebook, style='Card.TFrame')
        self.notebook.add(self.frame_produtos, text="🍔 Produtos")
        self.criar_interface_produtos(self.frame_produtos)

        self.frame_clientes = ttk.Frame(self.notebook, style='Card.TFrame')
        self.notebook.add(self.frame_clientes, text="👥 Clientes")
        self.criar_interface_clientes(self.frame_clientes)

        self.frame_pedidos = ttk.Frame(self.notebook, style='Card.TFrame')
        self.notebook.add(self.frame_pedidos, text="📋 Pedidos")
        self.criar_interface_pedidos(self.frame_pedidos)

        self.frame_relatorios = ttk.Frame(self.notebook, style='Card.TFrame')
        self.notebook.add(self.frame_relatorios, text="📊 Relatórios")
        self.criar_interface_relatorios(self.frame_relatorios)

        # Mensagem de feedback na parte inferior
        self.message_label = ttk.Label(master, text="", style='Feedback.TLabel', anchor='center')
        self.message_label.pack(side="bottom", fill="x", padx=10, pady=5)

        self.atualizar_todas_as_listas_e_comboboxes()
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_change)
        master.protocol("WM_DELETE_WINDOW", self.on_closing)

        # self.carrinho_pdv = {} # Esta linha foi movida para cima

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use('clam') # Um tema mais neutro para começar

        # Estilo para Frames (background)
        self.style.configure('TFrame', background=self.BACKGROUND_COLOR)
        self.style.configure('Card.TFrame', background=self.BACKGROUND_COLOR) # Para frames das abas

        # Estilo para Labels
        self.style.configure('TLabel', background=self.BACKGROUND_COLOR, foreground=self.TEXT_COLOR, font=('Arial', 10))
        self.style.configure('Header.TLabel', font=('Arial', 12, 'bold'), foreground=self.HEADER_COLOR, background=self.BACKGROUND_COLOR)
        self.style.configure('Feedback.TLabel', font=('Arial', 10, 'italic'), foreground='blue', background=self.BACKGROUND_COLOR) # Para mensagens de feedback

        # Estilo para Buttons
        self.style.configure('TButton', font=('Arial', 10, 'bold'), padding=8, background=self.PRIMARY_COLOR, foreground='white')
        self.style.map('TButton', 
                       background=[('active', self.PRIMARY_COLOR)],
                       foreground=[('active', 'white')]) # Cor do texto não muda no hover

        # Estilo para Entry e Combobox
        self.style.configure('TEntry', padding=5, font=('Arial', 10))
        self.style.configure('TCombobox', padding=5, font=('Arial', 10))

        # Estilo para Treeview (listas)
        self.style.configure("Treeview", 
                             background="white", 
                             foreground=self.TEXT_COLOR, 
                             rowheight=25, 
                             fieldbackground="white",
                             font=('Arial', 10))
        self.style.map('Treeview', 
                       background=[('selected', self.PRIMARY_COLOR)]) # Item selecionado
        self.style.configure("Treeview.Heading", 
                             font=('Arial', 10, 'bold'), 
                             background=self.HEADER_COLOR, 
                             foreground='white')
        self.style.map("Treeview.Heading", 
                       background=[('active', self.HEADER_COLOR)]) # Cabeçalho não muda no hover

        # Estilo para LabelFrame
        self.style.configure('TLabelframe', background=self.BACKGROUND_COLOR, bordercolor=self.HEADER_COLOR, relief='solid')
        self.style.configure('TLabelframe.Label', background=self.BACKGROUND_COLOR, foreground=self.HEADER_COLOR, font=('Arial', 11, 'bold'))

        # Estilo para Notebook Tabs
        self.style.configure('TNotebook', background=self.BACKGROUND_COLOR, borderwidth=0)
        self.style.configure('TNotebook.Tab', 
                             background=self.HEADER_COLOR, 
                             foreground='white', 
                             padding=[10, 5],
                             font=('Arial', 11, 'bold'))
        self.style.map('TNotebook.Tab', 
                       background=[('selected', self.PRIMARY_COLOR)], 
                       foreground=[('selected', 'white')])


    def on_closing(self):
        """Função para salvar dados ao fechar a janela."""
        if messagebox.askokcancel("Sair", "Deseja salvar os dados e sair?"):
            self.lanchonete.salvar_dados()
            self.master.destroy()

    def on_tab_change(self, event):
        selected_tab = self.notebook.tab(self.notebook.select(), "text")
        if "Produtos" in selected_tab: # Usando "in" para ser mais flexível com ícones
            self.atualizar_lista_produtos()
        elif "Clientes" in selected_tab:
            self.atualizar_lista_clientes()
        elif "Pedidos" in selected_tab:
            self.atualizar_lista_pedidos(self.filter_status_combo.get())
            self.atualizar_comboboxes_pedido() 
        elif "Relatórios" in selected_tab:
            self.limpar_relatorio_display()
            self.atualizar_comboboxes_relatorio() 
        elif "Vendas (PDV)" in selected_tab:
            self.atualizar_comboboxes_vendas()
            self.atualizar_lista_produtos_pdv()
            self.limpar_carrinho_pdv_gui() # Limpa o carrinho ao mudar para a aba

    def atualizar_todas_as_listas_e_comboboxes(self):
        """Chama todas as funções de atualização necessárias."""
        self.atualizar_lista_produtos()
        self.atualizar_lista_clientes()
        self.atualizar_lista_pedidos()
        self.atualizar_comboboxes_pedido()
        self.atualizar_comboboxes_relatorio()
        self.atualizar_comboboxes_vendas()
        self.atualizar_lista_produtos_pdv()
        self.atualizar_carrinho_pdv_gui() # Garante que o carrinho está vazio ao iniciar

    def exibir_mensagem(self, message: str, is_error: bool = False):
        """Exibe mensagens de feedback com estilo."""
        if is_error:
            self.message_label.config(text=f"ERRO: {message}", foreground=self.style.lookup('TLabel', 'foreground', default='red'))
            messagebox.showerror("Erro", message)
        else:
            self.message_label.config(text=message, foreground=self.style.lookup('Feedback.TLabel', 'foreground', default='blue'))
        self.master.after(5000, lambda: self.message_label.config(text="", foreground="blue")) # Limpa a mensagem após 5 segundos

    # --- Interface de Produtos ---
    def criar_interface_produtos(self, parent_frame):
        input_frame = ttk.LabelFrame(parent_frame, text="Gerenciar Produtos", padding="15")
        input_frame.pack(fill="x", padx=10, pady=10)

        # Usando grid para melhor alinhamento
        input_frame.columnconfigure(1, weight=1) # Faz a coluna de entrada expandir

        ttk.Label(input_frame, text="ID do Produto:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.prod_id_entry = ttk.Entry(input_frame, width=30)
        self.prod_id_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(input_frame, text="Nome:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.prod_nome_entry = ttk.Entry(input_frame, width=40)
        self.prod_nome_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(input_frame, text="Preço (R$):").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.prod_preco_entry = ttk.Entry(input_frame, width=20)
        self.prod_preco_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(input_frame, text="Estoque:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.prod_estoque_entry = ttk.Entry(input_frame, width=20)
        self.prod_estoque_entry.grid(row=3, column=1, padx=5, pady=5, sticky="ew")

        self.prod_disponivel_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(input_frame, text="Produto Disponível", variable=self.prod_disponivel_var).grid(row=4, column=1, padx=5, pady=5, sticky="w")

        button_frame = ttk.Frame(input_frame)
        button_frame.grid(row=5, column=0, columnspan=2, pady=10)

        ttk.Button(button_frame, text="➕ Adicionar", command=self.adicionar_produto_gui, style='TButton').pack(side="left", padx=5)
        ttk.Button(button_frame, text="🗑️ Remover", command=self.remover_produto_gui, style='TButton').pack(side="left", padx=5)
        ttk.Button(button_frame, text="✏️ Atualizar Dados", command=self.atualizar_produto_gui, style='TButton').pack(side="left", padx=5)
        ttk.Button(button_frame, text="🔄 Atualizar Disponibilidade", command=self.atualizar_disponibilidade_produto_gui, style='TButton').pack(side="left", padx=5)
        ttk.Button(button_frame, text="🧹 Limpar Campos", command=self.limpar_campos_produto, style='TButton').pack(side="left", padx=5)


        list_frame = ttk.LabelFrame(parent_frame, text="Cardápio Atual", padding="15")
        list_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.tree_produtos = ttk.Treeview(list_frame, columns=("ID", "Nome", "Preço", "Estoque", "Disponível"), show="headings", style="Treeview")
        self.tree_produtos.heading("ID", text="ID")
        self.tree_produtos.heading("Nome", text="Nome")
        self.tree_produtos.heading("Preço", text="Preço")
        self.tree_produtos.heading("Estoque", text="Estoque")
        self.tree_produtos.heading("Disponível", text="Disponível")

        self.tree_produtos.column("ID", width=100, anchor="center")
        self.tree_produtos.column("Nome", width=250)
        self.tree_produtos.column("Preço", width=100, anchor="e")
        self.tree_produtos.column("Estoque", width=100, anchor="center")
        self.tree_produtos.column("Disponível", width=100, anchor="center")

        self.tree_produtos.pack(side="left", fill="both", expand=True)

        scrollbar_y = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree_produtos.yview)
        scrollbar_y.pack(side="right", fill="y")
        self.tree_produtos.config(yscrollcommand=scrollbar_y.set)

        self.tree_produtos.bind("<ButtonRelease-1>", self.carregar_produto_selecionado)

    def adicionar_produto_gui(self):
        id_prod = self.prod_id_entry.get().strip()
        nome_prod = self.prod_nome_entry.get().strip()
        preco_str = self.prod_preco_entry.get().strip()
        estoque_str = self.prod_estoque_entry.get().strip()
        disponivel = self.prod_disponivel_var.get()

        if not id_prod or not nome_prod or not preco_str or not estoque_str:
            self.exibir_mensagem("Preencha todos os campos (ID, Nome, Preço, Estoque).", True)
            return
        
        try:
            preco_prod = float(preco_str)
            if preco_prod <= 0:
                self.exibir_mensagem("Preço deve ser maior que zero.", True)
                return
        except ValueError:
            self.exibir_mensagem("Preço inválido. Use um número (ex: 25.50).", True)
            return
        
        try:
            estoque_prod = int(estoque_str)
            if estoque_prod < 0:
                self.exibir_mensagem("Estoque inicial não pode ser negativo.", True)
                return
        except ValueError:
            self.exibir_mensagem("Estoque inválido. Use um número inteiro.", True)
            return

        novo_produto = Produto(id_prod, nome_prod, preco_prod, disponivel, estoque_prod)
        success, message = self.lanchonete.adicionar_produto(novo_produto)
        self.exibir_mensagem(message, not success)
        if success:
            self.atualizar_lista_produtos()
            self.limpar_campos_produto()
            self.atualizar_comboboxes_pedido() 
            self.atualizar_comboboxes_vendas()
            self.atualizar_lista_produtos_pdv()

    def remover_produto_gui(self):
        selected_item = self.tree_produtos.selection()
        if not selected_item:
            self.exibir_mensagem("Selecione um produto para remover.", True)
            return
        
        id_prod = self.tree_produtos.item(selected_item, "values")[0]
        if not messagebox.askyesno("Confirmar Remoção", f"Tem certeza que deseja remover o produto {id_prod}?"):
            return

        success, message = self.lanchonete.remover_produto(id_prod)
        self.exibir_mensagem(message, not success)
        if success:
            self.atualizar_lista_produtos()
            self.limpar_campos_produto()
            self.atualizar_comboboxes_pedido() 
            self.atualizar_comboboxes_vendas()
            self.atualizar_lista_produtos_pdv()


    def atualizar_produto_gui(self):
        selected_item = self.tree_produtos.selection()
        if not selected_item:
            self.exibir_mensagem("Selecione um produto para atualizar os dados.", True)
            return

        original_id_prod = self.tree_produtos.item(selected_item, "values")[0]
        
        nome_prod = self.prod_nome_entry.get().strip()
        preco_str = self.prod_preco_entry.get().strip()
        estoque_str = self.prod_estoque_entry.get().strip()

        preco_prod = None
        if preco_str:
            try:
                preco_prod = float(preco_str)
                if preco_prod <= 0:
                    self.exibir_mensagem("Preço deve ser maior que zero.", True)
                    return
            except ValueError:
                self.exibir_mensagem("Preço inválido. Use um número (ex: 25.50).", True)
                return
        
        estoque_prod = None
        if estoque_str:
            try:
                estoque_prod = int(estoque_str)
                if estoque_prod < 0:
                    self.exibir_mensagem("Estoque não pode ser negativo.", True)
                    return
            except ValueError:
                self.exibir_mensagem("Estoque inválido. Use um número inteiro.", True)
                return
        
        if not nome_prod and preco_prod is None and estoque_prod is None:
            self.exibir_mensagem("Preencha ao menos um campo (Nome, Preço ou Estoque) para atualizar.", True)
            return

        success, message = self.lanchonete.atualizar_produto_info(
            original_id_prod, 
            nome_prod if nome_prod else None, 
            preco_prod,
            estoque_prod
        )
        self.exibir_mensagem(message, not success)
        if success:
            self.atualizar_lista_produtos()
            self.limpar_campos_produto()
            self.atualizar_comboboxes_pedido() 
            self.atualizar_comboboxes_vendas()
            self.atualizar_lista_produtos_pdv()


    def atualizar_disponibilidade_produto_gui(self):
        selected_item = self.tree_produtos.selection()
        if not selected_item:
            self.exibir_mensagem("Selecione um produto para atualizar a disponibilidade.", True)
            return
        
        id_prod = self.tree_produtos.item(selected_item, "values")[0]
        disponivel = self.prod_disponivel_var.get()

        success, message = self.lanchonete.atualizar_disponibilidade_produto(id_prod, disponivel)
        self.exibir_mensagem(message, not success)
        if success:
            self.atualizar_lista_produtos()
            self.atualizar_lista_produtos_pdv()

    def atualizar_lista_produtos(self):
        for item in self.tree_produtos.get_children():
            self.tree_produtos.delete(item)
        
        for produto in self.lanchonete.cardapio.values():
            self.tree_produtos.insert("", "end", values=(produto.id_produto, produto.nome, f"{produto.preco:.2f}", produto.estoque, "Sim" if produto.disponivel else "Não"))

    def carregar_produto_selecionado(self, event):
        selected_item = self.tree_produtos.selection()
        if selected_item:
            values = self.tree_produtos.item(selected_item, "values")
            self.prod_id_entry.delete(0, tk.END)
            self.prod_id_entry.insert(0, values[0])
            self.prod_nome_entry.delete(0, tk.END)
            self.prod_nome_entry.insert(0, values[1])
            self.prod_preco_entry.delete(0, tk.END)
            self.prod_preco_entry.insert(0, values[2])
            self.prod_estoque_entry.delete(0, tk.END)
            self.prod_estoque_entry.insert(0, values[3])
            self.prod_disponivel_var.set(True if values[4] == "Sim" else False)
            self.manage_pedido_produto_id_combo.set(values[0])

    def limpar_campos_produto(self):
        self.prod_id_entry.delete(0, tk.END)
        self.prod_nome_entry.delete(0, tk.END)
        self.prod_preco_entry.delete(0, tk.END)
        self.prod_estoque_entry.delete(0, tk.END)
        self.prod_disponivel_var.set(True)


    # --- Interface de Clientes ---
    def criar_interface_clientes(self, parent_frame):
        input_frame = ttk.LabelFrame(parent_frame, text="Gerenciar Clientes", padding="15")
        input_frame.pack(fill="x", padx=10, pady=10)

        input_frame.columnconfigure(1, weight=1)

        ttk.Label(input_frame, text="ID do Cliente:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.cli_id_entry = ttk.Entry(input_frame, width=30)
        self.cli_id_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(input_frame, text="Nome:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.cli_nome_entry = ttk.Entry(input_frame, width=40)
        self.cli_nome_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(input_frame, text="Telefone:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.cli_tel_entry = ttk.Entry(input_frame, width=20)
        self.cli_tel_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(input_frame, text="Endereço:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.cli_end_entry = ttk.Entry(input_frame, width=40)
        self.cli_end_entry.grid(row=3, column=1, padx=5, pady=5, sticky="ew")

        button_frame = ttk.Frame(input_frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=10)

        ttk.Button(button_frame, text="➕ Cadastrar", command=self.cadastrar_cliente_gui, style='TButton').pack(side="left", padx=5)
        ttk.Button(button_frame, text="✏️ Atualizar", command=self.atualizar_cliente_gui, style='TButton').pack(side="left", padx=5)
        ttk.Button(button_frame, text="🧹 Limpar Campos", command=self.limpar_campos_cliente, style='TButton').pack(side="left", padx=5)


        list_frame = ttk.LabelFrame(parent_frame, text="Clientes Cadastrados", padding="15")
        list_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.tree_clientes = ttk.Treeview(list_frame, columns=("ID", "Nome", "Telefone", "Endereço"), show="headings", style="Treeview")
        self.tree_clientes.heading("ID", text="ID")
        self.tree_clientes.heading("Nome", text="Nome")
        self.tree_clientes.heading("Telefone", text="Telefone")
        self.tree_clientes.heading("Endereço", text="Endereço")

        self.tree_clientes.column("ID", width=100, anchor="center")
        self.tree_clientes.column("Nome", width=200)
        self.tree_clientes.column("Telefone", width=120, anchor="center")
        self.tree_clientes.column("Endereço", width=300)

        self.tree_clientes.pack(side="left", fill="both", expand=True)

        scrollbar_y = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree_clientes.yview)
        scrollbar_y.pack(side="right", fill="y")
        self.tree_clientes.config(yscrollcommand=scrollbar_y.set)

        self.tree_clientes.bind("<ButtonRelease-1>", self.carregar_cliente_selecionado)

    def cadastrar_cliente_gui(self):
        id_cli = self.cli_id_entry.get().strip()
        nome_cli = self.cli_nome_entry.get().strip()
        tel_cli = self.cli_tel_entry.get().strip()
        end_cli = self.cli_end_entry.get().strip()

        if not id_cli or not nome_cli or not tel_cli:
            self.exibir_mensagem("ID, Nome e Telefone são obrigatórios para o cliente.", True)
            return

        novo_cliente = Cliente(id_cli, nome_cli, tel_cli, end_cli if end_cli else None)
        success, message = self.lanchonete.cadastrar_cliente(novo_cliente)
        self.exibir_mensagem(message, not success)
        if success:
            self.atualizar_lista_clientes()
            self.limpar_campos_cliente()
            self.atualizar_comboboxes_pedido() 
            self.atualizar_comboboxes_relatorio() 
            self.atualizar_comboboxes_vendas()

    def atualizar_cliente_gui(self):
        selected_item = self.tree_clientes.selection()
        if not selected_item:
            self.exibir_mensagem("Selecione um cliente para atualizar.", True)
            return
        
        original_id_cli = self.tree_clientes.item(selected_item, "values")[0]
        
        nome_cli = self.cli_nome_entry.get().strip()
        tel_cli = self.cli_tel_entry.get().strip()
        end_cli = self.cli_end_entry.get().strip()

        id_para_atualizar = original_id_cli

        if not nome_cli and not tel_cli and not end_cli:
            self.exibir_mensagem("Preencha ao menos um campo (Nome, Telefone ou Endereço) para atualizar.", True)
            return

        success, message = self.lanchonete.atualizar_info_cliente(
            id_para_atualizar, 
            nome_cli if nome_cli else None,
            tel_cli if tel_cli else None,
            end_cli if end_cli else None
        )
        self.exibir_mensagem(message, not success)
        if success:
            self.atualizar_lista_clientes()
            self.limpar_campos_cliente()
            self.atualizar_comboboxes_pedido() 
            self.atualizar_comboboxes_relatorio() 
            self.atualizar_comboboxes_vendas()


    def atualizar_lista_clientes(self):
        for item in self.tree_clientes.get_children():
            self.tree_clientes.delete(item)
        
        for cliente in self.lanchonete.clientes.values():
            self.tree_clientes.insert("", "end", values=(cliente.id_cliente, cliente.nome, cliente.telefone, cliente.endereco))

    def carregar_cliente_selecionado(self, event):
        selected_item = self.tree_clientes.selection()
        if selected_item:
            values = self.tree_clientes.item(selected_item, "values")
            self.cli_id_entry.delete(0, tk.END)
            self.cli_id_entry.insert(0, values[0])
            self.cli_nome_entry.delete(0, tk.END)
            self.cli_nome_entry.insert(0, values[1])
            self.cli_tel_entry.delete(0, tk.END)
            self.cli_tel_entry.insert(0, values[2])
            self.cli_end_entry.delete(0, tk.END)
            self.cli_end_entry.insert(0, values[3])
            self.pedido_cliente_id_combo.set(values[0]) 
            self.rel_pedidos_cliente_id_combo.set(values[0]) 
            self.vendas_cliente_id_combo.set(values[0])

    def limpar_campos_cliente(self):
        self.cli_id_entry.delete(0, tk.END)
        self.cli_nome_entry.delete(0, tk.END)
        self.cli_tel_entry.delete(0, tk.END)
        self.cli_end_entry.delete(0, tk.END)

    # --- Interface de Pedidos ---
    def criar_interface_pedidos(self, parent_frame):
        # Frame para criar pedido
        create_order_frame = ttk.LabelFrame(parent_frame, text="Criar Novo Pedido", padding="15")
        create_order_frame.pack(fill="x", padx=10, pady=10)
        create_order_frame.columnconfigure(1, weight=1)

        ttk.Label(create_order_frame, text="Cliente:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.pedido_cliente_id_combo = ttk.Combobox(create_order_frame, state="readonly")
        self.pedido_cliente_id_combo.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.pedido_cliente_id_combo.bind("<<ComboboxSelected>>", self.on_cliente_selecionado_pedido)
        
        ttk.Button(create_order_frame, text="➕ Criar Pedido", command=self.criar_pedido_gui, style='TButton').grid(row=0, column=2, padx=5, pady=5)


        # Frame para adicionar/remover itens e atualizar status
        manage_order_frame = ttk.LabelFrame(parent_frame, text="Gerenciar Pedido Existente", padding="15")
        manage_order_frame.pack(fill="x", padx=10, pady=10)
        manage_order_frame.columnconfigure(1, weight=1)

        ttk.Label(manage_order_frame, text="ID Pedido:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.manage_pedido_id_entry = ttk.Entry(manage_order_frame)
        self.manage_pedido_id_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(manage_order_frame, text="🔍 Buscar Pedido", command=self.buscar_pedido_gui, style='TButton').grid(row=0, column=2, padx=5, pady=5)

        ttk.Label(manage_order_frame, text="Produto:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.manage_pedido_produto_id_combo = ttk.Combobox(manage_order_frame, state="readonly")
        self.manage_pedido_produto_id_combo.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        
        ttk.Label(manage_order_frame, text="Quantidade:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.pedido_quantidade_entry = ttk.Entry(manage_order_frame)
        self.pedido_quantidade_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        button_frame_itens = ttk.Frame(manage_order_frame)
        button_frame_itens.grid(row=3, column=0, columnspan=3, pady=10)
        ttk.Button(button_frame_itens, text="➕ Adicionar Item", command=self.adicionar_item_pedido_gui, style='TButton').pack(side="left", padx=5)
        ttk.Button(button_frame_itens, text="➖ Remover Item", command=self.remover_item_pedido_gui, style='TButton').pack(side="left", padx=5)
        ttk.Button(button_frame_itens, text="🧹 Limpar Campos", command=self.limpar_campos_item_pedido, style='TButton').pack(side="left", padx=5)
        
        ttk.Label(manage_order_frame, text="Status:").grid(row=4, column=0, padx=5, pady=5, sticky="w")
        self.pedido_status_combo = ttk.Combobox(manage_order_frame, 
                                                values=["Pendente", "Em Preparo", "Pronto", "Entregue", "Cancelado"],
                                                state="readonly")
        self.pedido_status_combo.grid(row=4, column=1, padx=5, pady=5, sticky="ew")
        self.pedido_status_combo.set("Pendente")
        ttk.Button(manage_order_frame, text="🔄 Atualizar Status", command=self.atualizar_status_pedido_gui, style='TButton').grid(row=4, column=2, padx=5, pady=5)

        # Frame para exibir pedidos (Treeview)
        list_frame = ttk.LabelFrame(parent_frame, text="Lista de Pedidos", padding="15")
        list_frame.pack(fill="both", expand=True, padx=10, pady=10)

        filter_frame = ttk.Frame(list_frame)
        filter_frame.pack(fill="x", pady=5)
        ttk.Label(filter_frame, text="Filtrar por Status:").pack(side="left", padx=5)
        self.filter_status_combo = ttk.Combobox(filter_frame, 
                                                values=["Todos", "Pendente", "Em Preparo", "Pronto", "Entregue", "Cancelado"],
                                                state="readonly", width=15)
        self.filter_status_combo.set("Todos")
        self.filter_status_combo.pack(side="left", padx=5)
        self.filter_status_combo.bind("<<ComboboxSelected>>", self.aplicar_filtro_pedidos)
        ttk.Button(filter_frame, text="🔎 Mostrar Todos", command=lambda: self.filter_status_combo.set("Todos") or self.aplicar_filtro_pedidos(None), style='TButton').pack(side="left", padx=5)


        self.tree_pedidos = ttk.Treeview(list_frame, columns=("ID Pedido", "ID Cliente", "Status", "Total", "Data/Hora", "Itens"), show="headings", style="Treeview")
        self.tree_pedidos.heading("ID Pedido", text="ID Pedido")
        self.tree_pedidos.heading("ID Cliente", text="ID Cliente")
        self.tree_pedidos.heading("Status", text="Status")
        self.tree_pedidos.heading("Total", text="Total")
        self.tree_pedidos.heading("Data/Hora", text="Data/Hora")
        self.tree_pedidos.heading("Itens", text="Itens (Nome: Qtd)")

        self.tree_pedidos.column("ID Pedido", width=100, anchor="center")
        self.tree_pedidos.column("ID Cliente", width=100, anchor="center")
        self.tree_pedidos.column("Status", width=100, anchor="center")
        self.tree_pedidos.column("Total", width=90, anchor="e")
        self.tree_pedidos.column("Data/Hora", width=140, anchor="center")
        self.tree_pedidos.column("Itens", width=350) 

        self.tree_pedidos.pack(side="left", fill="both", expand=True)

        scrollbar_y = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree_pedidos.yview)
        scrollbar_y.pack(side="right", fill="y")
        self.tree_pedidos.config(yscrollcommand=scrollbar_y.set)

        self.tree_pedidos.bind("<ButtonRelease-1>", self.carregar_pedido_selecionado)

    def atualizar_comboboxes_pedido(self):
        clientes_ids = sorted(list(self.lanchonete.clientes.keys()))
        self.pedido_cliente_id_combo['values'] = clientes_ids
        if clientes_ids:
            self.pedido_cliente_id_combo.set(clientes_ids[0])
        else:
            self.pedido_cliente_id_combo.set("")

        produtos_ids = sorted(list(self.lanchonete.cardapio.keys()))
        self.manage_pedido_produto_id_combo['values'] = produtos_ids
        if produtos_ids:
            self.manage_pedido_produto_id_combo.set(produtos_ids[0])
        else:
            self.manage_pedido_produto_id_combo.set("")

    def on_cliente_selecionado_pedido(self, event):
        selected_client_id = self.pedido_cliente_id_combo.get()

    def criar_pedido_gui(self):
        id_cli = self.pedido_cliente_id_combo.get().strip() 
        if not id_cli:
            self.exibir_mensagem("Selecione um Cliente para criar um pedido.", True)
            return

        success, message, novo_pedido = self.lanchonete.criar_pedido(id_cli)
        self.exibir_mensagem(message, not success)
        if success:
            self.atualizar_lista_pedidos(self.filter_status_combo.get())
            if novo_pedido:
                self.manage_pedido_id_entry.delete(0, tk.END)
                self.manage_pedido_id_entry.insert(0, novo_pedido.id_pedido)
            self.pedido_cliente_id_combo.set(id_cli) 
            self.limpar_campos_item_pedido() 

    def adicionar_item_a_pedido(self, id_pedido: str, id_produto: str, quantidade: int) -> tuple[bool, str]:
        pedido = self.pedidos.get(id_pedido)
        if not pedido:
            return False, f"Erro: Pedido com ID '{id_pedido}' não encontrado."
        produto = self.cardapio.get(id_produto)
        if not produto:
            return False, f"Erro: Produto com ID '{id_produto}' não encontrado no cardápio."
        
        if quantidade <= 0:
            return False, "Erro: Quantidade do item deve ser maior que zero."

        # A lógica de verificar estoque foi adicionada para refletir a nova responsabilidade do PDV
        if produto.estoque < quantidade:
            return False, f"Estoque insuficiente para '{produto.nome}'. Disponível: {produto.estoque}"

        success, message = pedido.adicionar_item(produto, quantidade)
        if success:
            # Deduz o estoque imediatamente ao adicionar ao pedido
            produto.estoque -= quantidade
            self.salvar_dados()
            return True, f"Item '{produto.nome}' (x{quantidade}) adicionado ao pedido {id_pedido}."
        else:
            return False, message

    def adicionar_item_pedido_gui(self):
        id_ped = self.manage_pedido_id_entry.get().strip()
        id_prod = self.manage_pedido_produto_id_combo.get().strip() 
        qtd_str = self.pedido_quantidade_entry.get().strip()

        if not id_ped:
            self.exibir_mensagem("Selecione ou digite o ID do Pedido.", True)
            return
        if not id_prod:
            self.exibir_mensagem("Selecione um Produto para adicionar.", True)
            return
        if not qtd_str:
            self.exibir_mensagem("Quantidade é obrigatória.", True)
            return
        
        try:
            quantidade = int(qtd_str)
            if quantidade <= 0:
                self.exibir_mensagem("Quantidade deve ser um número inteiro positivo.", True)
                return
        except ValueError:
            self.exibir_mensagem("Quantidade inválida. Use um número inteiro.", True)
            return

        # A chamada para self.lanchonete.adicionar_item_a_pedido agora deve lidar com a dedução do estoque.
        # Ajustei o método lanchonete.adicionar_item_a_pedido para fazer essa dedução.
        success, message = self.lanchonete.adicionar_item_a_pedido(id_ped, id_prod, quantidade)
        self.exibir_mensagem(message, not success)
        if success:
            self.atualizar_lista_pedidos(self.filter_status_combo.get())
            self.limpar_campos_item_pedido()
            self.atualizar_lista_produtos() # Atualiza a lista de produtos para refletir a mudança no estoque
            self.carregar_pedido_selecionado(None)


    def remover_item_de_pedido(self, id_pedido: str, id_produto: str) -> tuple[bool, str]:
        pedido = self.pedidos.get(id_pedido)
        if not pedido:
            return False, f"Erro: Pedido com ID '{id_pedido}' não encontrado."
        
        item_removido = None
        produto_original = None
        for item in pedido.itens:
            if item.produto.id_produto == id_produto:
                item_removido = item
                produto_original = item.produto # Guarda a referência ao produto original
                break

        if item_removido:
            pedido.itens.remove(item_removido)
            pedido.valor_total -= item_removido.subtotal
            
            # Devolve o estoque ao produto quando o item é removido do pedido
            if produto_original:
                produto_original.estoque += item_removido.quantidade
            
            self.salvar_dados()
            return True, f"Item '{item_removido.produto.nome}' removido do pedido {id_pedido} e estoque restituído."
        return False, f"Produto com ID '{id_produto}' não encontrado no pedido {id_pedido}."

    def remover_item_pedido_gui(self):
        id_ped = self.manage_pedido_id_entry.get().strip()
        id_prod = self.manage_pedido_produto_id_combo.get().strip() 

        if not id_ped:
            self.exibir_mensagem("Selecione ou digite o ID do Pedido.", True)
            return
        if not id_prod:
            self.exibir_mensagem("Selecione um Produto para remover.", True)
            return
        
        if not messagebox.askyesno("Confirmar Remoção", f"Tem certeza que deseja remover o item {id_prod} do pedido {id_ped}?"):
            return

        success, message = self.lanchonete.remover_item_de_pedido(id_ped, id_prod)
        self.exibir_mensagem(message, not success)
        if success:
            self.atualizar_lista_pedidos(self.filter_status_combo.get())
            self.limpar_campos_item_pedido()
            self.atualizar_lista_produtos() # Atualiza a lista de produtos para refletir a mudança no estoque
            self.carregar_pedido_selecionado(None)

    def atualizar_status_pedido_gui(self):
        id_ped = self.manage_pedido_id_entry.get().strip()
        novo_status = self.pedido_status_combo.get()

        if not id_ped or not novo_status:
            self.exibir_mensagem("ID do Pedido e Status são obrigatórios.", True)
            return

        success, message = self.lanchonete.atualizar_status_pedido(id_ped, novo_status)
        self.exibir_mensagem(message, not success)
        if success:
            self.atualizar_lista_pedidos(self.filter_status_combo.get())
            self.atualizar_lista_produtos()

    def buscar_pedido_gui(self):
        id_ped = self.manage_pedido_id_entry.get().strip()
        if not id_ped:
            self.exibir_mensagem("Digite o ID do Pedido para buscar.", True)
            return
        
        pedido = self.lanchonete.buscar_pedido(id_ped)
        if pedido:
            self.exibir_mensagem(f"Pedido {pedido.id_pedido} encontrado. Status: {pedido.status}", False)
            self.pedido_status_combo.set(pedido.status)
            self.pedido_cliente_id_combo.set(pedido.id_cliente) 

            for item_id in self.tree_pedidos.get_children():
                if self.tree_pedidos.item(item_id, 'values')[0] == id_ped:
                    self.tree_pedidos.selection_set(item_id)
                    self.tree_pedidos.focus(item_id)
                    self.tree_pedidos.see(item_id)
                    break
        else:
            self.exibir_mensagem(f"Pedido com ID '{id_ped}' não encontrado.", True)


    def atualizar_lista_pedidos(self, status_filtro: str = "Todos"):
        for item in self.tree_pedidos.get_children():
            self.tree_pedidos.delete(item)
        
        pedidos_para_exibir = []
        if status_filtro == "Todos":
            pedidos_para_exibir = list(self.lanchonete.pedidos.values())
        else:
            pedidos_para_exibir = [p for p in self.lanchonete.pedidos.values() if p.status == status_filtro]

        pedidos_para_exibir.sort(key=lambda p: p.data_hora_criacao, reverse=True)

        for pedido in pedidos_para_exibir:
            itens_resumo = ", ".join([f"{item.produto.nome} ({item.quantidade})" for item in pedido.itens])
            self.tree_pedidos.insert("", "end", values=(
                pedido.id_pedido, 
                pedido.id_cliente, 
                pedido.status, 
                f"{pedido.valor_total:.2f}",
                pedido.data_hora_criacao.strftime('%d/%m/%Y %H:%M'),
                itens_resumo
            ))
    
    def aplicar_filtro_pedidos(self, event=None):
        status_selecionado = self.filter_status_combo.get()
        self.atualizar_lista_pedidos(status_selecionado)

    def carregar_pedido_selecionado(self, event):
        selected_item = self.tree_pedidos.selection()
        if selected_item:
            values = self.tree_pedidos.item(selected_item, "values")
            self.manage_pedido_id_entry.delete(0, tk.END)
            self.manage_pedido_id_entry.insert(0, values[0])
            self.pedido_cliente_id_combo.set(values[1]) 
            self.pedido_status_combo.set(values[2])
            
            self.limpar_campos_item_pedido()

    def limpar_campos_item_pedido(self):
        self.pedido_quantidade_entry.delete(0, tk.END)


    # --- Interface de Relatórios ---
    def criar_interface_relatorios(self, parent_frame):
        # Frame para Total de Vendas
        vendas_frame = ttk.LabelFrame(parent_frame, text="Total de Vendas por Período", padding="15")
        vendas_frame.pack(fill="x", padx=10, pady=10)
        vendas_frame.columnconfigure(1, weight=1)

        ttk.Label(vendas_frame, text="Data Início (AAAA-MM-DD):").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.vendas_data_inicio_entry = ttk.Entry(vendas_frame, width=15)
        self.vendas_data_inicio_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(vendas_frame, text="Data Fim (AAAA-MM-DD):").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.vendas_data_fim_entry = ttk.Entry(vendas_frame, width=15)
        self.vendas_data_fim_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        ttk.Button(vendas_frame, text="📈 Gerar Relatório de Vendas", command=self.gerar_relatorio_vendas_gui, style='TButton').grid(row=0, column=2, rowspan=2, padx=5, pady=5, sticky="ns")

        # Frame para Produtos Mais Vendidos
        top_products_frame = ttk.LabelFrame(parent_frame, text="Produtos Mais Vendidos", padding="15")
        top_products_frame.pack(fill="x", padx=10, pady=10)
        top_products_frame.columnconfigure(1, weight=1)

        ttk.Label(top_products_frame, text="Top N Produtos:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.top_n_products_entry = ttk.Entry(top_products_frame, width=5)
        self.top_n_products_entry.insert(0, "5")
        self.top_n_products_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Button(top_products_frame, text="📊 Gerar Relatório de Produtos", command=self.gerar_relatorio_top_produtos_gui, style='TButton').grid(row=0, column=2, padx=5, pady=5)

        # Frame para Pedidos por Cliente
        pedidos_cliente_frame = ttk.LabelFrame(parent_frame, text="Pedidos por Cliente", padding="15")
        pedidos_cliente_frame.pack(fill="x", padx=10, pady=10)
        pedidos_cliente_frame.columnconfigure(1, weight=1)

        ttk.Label(pedidos_cliente_frame, text="Cliente:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.rel_pedidos_cliente_id_combo = ttk.Combobox(pedidos_cliente_frame, state="readonly")
        self.rel_pedidos_cliente_id_combo.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.rel_pedidos_cliente_id_combo.bind("<<ComboboxSelected>>", self.on_cliente_selecionado_relatorio)

        ttk.Button(pedidos_cliente_frame, text="📜 Gerar Relatório de Cliente", command=self.gerar_relatorio_pedidos_cliente_gui, style='TButton').grid(row=0, column=2, padx=5, pady=5)


        self.relatorio_display = tk.Text(parent_frame, wrap="word", height=15, width=80, font=('Arial', 10), relief="flat", padx=10, pady=10)
        self.relatorio_display.pack(fill="both", expand=True, padx=10, pady=10)
        self.relatorio_display.config(state="disabled")

        rel_scrollbar = ttk.Scrollbar(parent_frame, command=self.relatorio_display.yview)
        rel_scrollbar.pack(side="right", fill="y", in_=self.relatorio_display)
        self.relatorio_display.config(yscrollcommand=rel_scrollbar.set)

    def atualizar_comboboxes_relatorio(self):
        clientes_ids = sorted(list(self.lanchonete.clientes.keys()))
        self.rel_pedidos_cliente_id_combo['values'] = clientes_ids
        if clientes_ids:
            self.rel_pedidos_cliente_id_combo.set(clientes_ids[0])
        else:
            self.rel_pedidos_cliente_id_combo.set("")

    def on_cliente_selecionado_relatorio(self, event):
        selected_client_id = self.rel_pedidos_cliente_id_combo.get()

    def limpar_relatorio_display(self):
        self.relatorio_display.config(state="normal")
        self.relatorio_display.delete("1.0", tk.END)
        self.relatorio_display.config(state="disabled")

    def escrever_no_relatorio_display(self, text):
        self.relatorio_display.config(state="normal")
        self.relatorio_display.insert(tk.END, text + "\n")
        self.relatorio_display.config(state="disabled")
        self.relatorio_display.see(tk.END)

    def gerar_relatorio_vendas_gui(self):
        self.limpar_relatorio_display()
        self.escrever_no_relatorio_display("--- Relatório de Total de Vendas por Período ---")

        data_inicio_str = self.vendas_data_inicio_entry.get().strip()
        data_fim_str = self.vendas_data_fim_entry.get().strip()

        data_inicio = None
        data_fim = None

        if data_inicio_str:
            try:
                data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d')
            except ValueError:
                self.exibir_mensagem("Formato de Data Início inválido. Use AAAA-MM-DD.", True)
                return

        if data_fim_str:
            try:
                data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
            except ValueError:
                self.exibir_mensagem("Formato de Data Fim inválido. Use AAAA-MM-DD.", True)
                return
        
        if data_inicio and data_fim and data_inicio > data_fim:
            self.exibir_mensagem("Data de início não pode ser posterior à data de fim.", True)
            return

        total_vendas = self.lanchonete.relatorio_total_vendas_por_periodo(data_inicio, data_fim)
        
        periodo_str = ""
        if data_inicio and data_fim:
            periodo_str = f" de {data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}"
        elif data_inicio:
            periodo_str = f" a partir de {data_inicio.strftime('%d/%m/%Y')}"
        elif data_fim:
            periodo_str = f" até {data_fim.strftime('%d/%m/%Y')}"

        self.escrever_no_relatorio_display(f"Total de Vendas Entregues{periodo_str}: R${total_vendas:.2f}")

    def gerar_relatorio_top_produtos_gui(self):
        self.limpar_relatorio_display()
        self.escrever_no_relatorio_display("--- Relatório de Produtos Mais Vendidos ---")

        top_n_str = self.top_n_products_entry.get().strip()
        top_n = 5
        if top_n_str:
            try:
                top_n = int(top_n_str)
                if top_n <= 0:
                    self.exibir_mensagem("Top N deve ser um número inteiro positivo.", True)
                    return
            except ValueError:
                self.exibir_mensagem("Top N inválido. Use um número inteiro.", True)
                return
        
        produtos_vendidos = self.lanchonete.relatorio_produtos_mais_vendidos(top_n)

        if not produtos_vendidos:
            self.escrever_no_relatorio_display("Nenhum produto vendido ainda.")
        else:
            for i, (nome_produto, quantidade) in enumerate(produtos_vendidos):
                self.escrever_no_relatorio_display(f"{i+1}. {nome_produto}: {quantidade} unidades vendidas")
    
    def gerar_relatorio_pedidos_cliente_gui(self):
        self.limpar_relatorio_display()
        self.escrever_no_relatorio_display("--- Relatório de Pedidos por Cliente ---")

        id_cli = self.rel_pedidos_cliente_id_combo.get().strip() 
        if not id_cli:
            self.exibir_mensagem("Selecione um Cliente para este relatório.", True)
            return

        cliente = self.lanchonete.buscar_cliente(id_cli)
        if not cliente: 
            self.exibir_mensagem(f"Cliente com ID '{id_cli}' não encontrado (isto não deveria acontecer com o combobox).", True)
            self.escrever_no_relatorio_display(f"Cliente com ID '{id_cli}' não encontrado.")
            return

        self.escrever_no_relatorio_display(f"Pedidos para o Cliente: {cliente.nome} (ID: {cliente.id_cliente})")
        
        pedidos_cliente = self.lanchonete.relatorio_pedidos_por_cliente(id_cli)

        if not pedidos_cliente:
            self.escrever_no_relatorio_display("Nenhum pedido encontrado para este cliente.")
        else:
            for pedido in pedidos_cliente:
                itens_str = ", ".join([f"{item.produto.nome} (x{item.quantidade})" for item in pedido.itens])
                self.escrever_no_relatorio_display(f"  Pedido ID: {pedido.id_pedido}")
                self.escrever_no_relatorio_display(f"  Status: {pedido.status}")
                self.escrever_no_relatorio_display(f"  Valor Total: R${pedido.valor_total:.2f}")
                self.escrever_no_relatorio_display(f"  Data/Hora: {pedido.data_hora_criacao.strftime('%d/%m/%Y %H:%M')}")
                self.escrever_no_relatorio_display(f"  Itens: {itens_str}")
                self.escrever_no_relatorio_display("-" * 30)

    # --- Nova Interface de Vendas (PDV) ---
    def criar_interface_vendas(self, parent_frame):
        # Usando Frame principal com dois subframes
        main_frame = ttk.Frame(parent_frame, padding="15")
        main_frame.pack(fill="both", expand=True)

        # Frame da Esquerda: Seleção de Produtos e Quantidade
        left_frame = ttk.Frame(main_frame, style='Card.TFrame', relief='solid', borderwidth=1)
        left_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        left_frame.columnconfigure(0, weight=1) # Faz a coluna de produtos expandir

        ttk.Label(left_frame, text="Produtos Disponíveis", style='Header.TLabel').pack(anchor="center", pady=10)
        
        self.tree_produtos_pdv = ttk.Treeview(left_frame, columns=("ID", "Nome", "Preço", "Estoque"), show="headings", style="Treeview")
        self.tree_produtos_pdv.heading("ID", text="ID")
        self.tree_produtos_pdv.heading("Nome", text="Nome")
        self.tree_produtos_pdv.heading("Preço", text="Preço")
        self.tree_produtos_pdv.heading("Estoque", text="Estoque")
        self.tree_produtos_pdv.column("ID", width=70, anchor="center")
        self.tree_produtos_pdv.column("Nome", width=180)
        self.tree_produtos_pdv.column("Preço", width=80, anchor="e")
        self.tree_produtos_pdv.column("Estoque", width=80, anchor="center")
        self.tree_produtos_pdv.pack(fill="both", expand=True, padx=10, pady=10)

        scrollbar_y_pdv_prod = ttk.Scrollbar(left_frame, orient="vertical", command=self.tree_produtos_pdv.yview)
        scrollbar_y_pdv_prod.pack(side="right", fill="y", in_=self.tree_produtos_pdv)
        self.tree_produtos_pdv.config(yscrollcommand=scrollbar_y_pdv_prod.set)
        
        # Frame para entrada de quantidade e botão adicionar
        add_item_frame = ttk.Frame(left_frame, padding="10")
        add_item_frame.pack(fill="x", pady=10)
        add_item_frame.columnconfigure(1, weight=1) # Faz a entry expandir

        ttk.Label(add_item_frame, text="Quantidade:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.pdv_quantidade_entry = ttk.Entry(add_item_frame, width=10)
        self.pdv_quantidade_entry.insert(0, "1")
        self.pdv_quantidade_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        ttk.Button(add_item_frame, text="➕ Adicionar ao Carrinho", command=self.adicionar_item_ao_carrinho_pdv, style='TButton').grid(row=0, column=2, padx=5, pady=5)


        # Frame da Direita: Carrinho de Compras e Finalização
        right_frame = ttk.Frame(main_frame, style='Card.TFrame', relief='solid', borderwidth=1)
        right_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)
        right_frame.columnconfigure(0, weight=1) # Faz a combobox de cliente expandir

        client_frame = ttk.LabelFrame(right_frame, text="Detalhes do Cliente", padding="10")
        client_frame.pack(fill="x", pady=10, padx=10)
        client_frame.columnconfigure(1, weight=1)

        ttk.Label(client_frame, text="Cliente:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.vendas_cliente_id_combo = ttk.Combobox(client_frame, state="readonly")
        self.vendas_cliente_id_combo.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.vendas_cliente_id_combo.bind("<<ComboboxSelected>>", self.on_cliente_selecionado_pdv)

        ttk.Label(right_frame, text="Carrinho de Compras", style='Header.TLabel').pack(anchor="center", pady=10)

        self.tree_carrinho_pdv = ttk.Treeview(right_frame, columns=("ID", "Produto", "Qtd", "Preço Unit.", "Subtotal"), show="headings", style="Treeview")
        self.tree_carrinho_pdv.heading("ID", text="ID")
        self.tree_carrinho_pdv.heading("Produto", text="Produto")
        self.tree_carrinho_pdv.heading("Qtd", text="Qtd")
        self.tree_carrinho_pdv.heading("Preço Unit.", text="P. Unit.")
        self.tree_carrinho_pdv.heading("Subtotal", text="Subtotal")
        self.tree_carrinho_pdv.column("ID", width=50, anchor="center")
        self.tree_carrinho_pdv.column("Produto", width=150)
        self.tree_carrinho_pdv.column("Qtd", width=50, anchor="center")
        self.tree_carrinho_pdv.column("Preço Unit.", width=80, anchor="e")
        self.tree_carrinho_pdv.column("Subtotal", width=90, anchor="e")
        self.tree_carrinho_pdv.pack(fill="both", expand=True, padx=10, pady=10)

        scrollbar_y_pdv_carrinho = ttk.Scrollbar(right_frame, orient="vertical", command=self.tree_carrinho_pdv.yview)
        scrollbar_y_pdv_carrinho.pack(side="right", fill="y", in_=self.tree_carrinho_pdv)
        self.tree_carrinho_pdv.config(yscrollcommand=scrollbar_y_pdv_carrinho.set)

        self.total_carrinho_label = ttk.Label(right_frame, text="TOTAL: R$ 0.00", font=('Arial', 16, 'bold'), foreground=self.PRIMARY_COLOR, anchor="e")
        self.total_carrinho_label.pack(fill="x", pady=15, padx=10)

        button_actions_frame = ttk.Frame(right_frame)
        button_actions_frame.pack(fill="x", pady=5, padx=10)
        ttk.Button(button_actions_frame, text="🗑️ Remover do Carrinho", command=self.remover_item_do_carrinho_pdv, style='TButton').pack(side="left", padx=5)
        ttk.Button(button_actions_frame, text="🧹 Limpar Carrinho", command=self.limpar_carrinho_pdv_gui, style='TButton').pack(side="left", padx=5)
        ttk.Button(button_actions_frame, text="✅ Finalizar Venda", command=self.finalizar_venda_pdv, style='TButton').pack(side="right", padx=5)

    def atualizar_comboboxes_vendas(self):
        clientes_ids = sorted(list(self.lanchonete.clientes.keys()))
        self.vendas_cliente_id_combo['values'] = clientes_ids
        if clientes_ids:
            self.vendas_cliente_id_combo.set(clientes_ids[0])
        else:
            self.vendas_cliente_id_combo.set("")

    def atualizar_lista_produtos_pdv(self):
        for item in self.tree_produtos_pdv.get_children():
            self.tree_produtos_pdv.delete(item)
        
        for produto in self.lanchonete.cardapio.values():
            if produto.disponivel and produto.estoque > 0:
                self.tree_produtos_pdv.insert("", "end", values=(produto.id_produto, produto.nome, f"{produto.preco:.2f}", produto.estoque))

    def atualizar_carrinho_pdv_gui(self):
        for item in self.tree_carrinho_pdv.get_children():
            self.tree_carrinho_pdv.delete(item)
        
        total_geral = 0.0
        for id_prod, item_data in self.carrinho_pdv.items():
            produto = item_data["produto"]
            quantidade = item_data["quantidade"]
            subtotal = produto.preco * quantidade
            total_geral += subtotal
            self.tree_carrinho_pdv.insert("", "end", values=(id_prod, produto.nome, quantidade, f"{produto.preco:.2f}", f"{subtotal:.2f}"))
        
        self.total_carrinho_label.config(text=f"TOTAL: R$ {total_geral:.2f}")

    def on_cliente_selecionado_pdv(self, event):
        pass

    def adicionar_item_ao_carrinho_pdv(self):
        selected_item = self.tree_produtos_pdv.selection()
        if not selected_item:
            self.exibir_mensagem("Selecione um produto da lista de 'Produtos Disponíveis' para adicionar.", True)
            return
        
        id_prod = self.tree_produtos_pdv.item(selected_item, "values")[0]
        produto = self.lanchonete.cardapio.get(id_prod)

        if not produto or not produto.disponivel:
            self.exibir_mensagem("Produto não encontrado ou não disponível para venda.", True)
            return

        qtd_str = self.pdv_quantidade_entry.get().strip()
        try:
            quantidade_a_adicionar = int(qtd_str)
            if quantidade_a_adicionar <= 0:
                self.exibir_mensagem("Quantidade deve ser um número inteiro positivo.", True)
                return
        except ValueError:
            self.exibir_mensagem("Quantidade inválida. Por favor, insira um número inteiro.", True)
            return
        
        quantidade_no_carrinho = self.carrinho_pdv.get(id_prod, {}).get("quantidade", 0)
        
        if (quantidade_no_carrinho + quantidade_a_adicionar) > produto.estoque:
            self.exibir_mensagem(f"Estoque insuficiente para '{produto.nome}'. Disponível: {produto.estoque}, já no carrinho: {quantidade_no_carrinho}.", True)
            return

        if id_prod in self.carrinho_pdv:
            self.carrinho_pdv[id_prod]["quantidade"] += quantidade_a_adicionar
        else:
            self.carrinho_pdv[id_prod] = {"produto": produto, "quantidade": quantidade_a_adicionar}
        
        self.exibir_mensagem(f"{quantidade_a_adicionar}x {produto.nome} adicionado(s) ao carrinho.")
        self.atualizar_carrinho_pdv_gui()
        self.pdv_quantidade_entry.delete(0, tk.END)
        self.pdv_quantidade_entry.insert(0, "1")


    def remover_item_do_carrinho_pdv(self):
        selected_item = self.tree_carrinho_pdv.selection()
        if not selected_item:
            self.exibir_mensagem("Selecione um item no 'Carrinho de Compras' para remover.", True)
            return
        
        id_prod = self.tree_carrinho_pdv.item(selected_item, "values")[0]
        
        if id_prod in self.carrinho_pdv:
            if messagebox.askyesno("Confirmar Remoção", f"Tem certeza que deseja remover '{self.carrinho_pdv[id_prod]['produto'].nome}' do carrinho?"):
                del self.carrinho_pdv[id_prod]
                self.exibir_mensagem("Item removido do carrinho.")
                self.atualizar_carrinho_pdv_gui()
        else:
            self.exibir_mensagem("Item não encontrado no carrinho.", True)

    def limpar_carrinho_pdv_gui(self):
        if not self.carrinho_pdv:
            self.exibir_mensagem("O carrinho já está vazio.", True)
            return

        if messagebox.askyesno("Limpar Carrinho", "Tem certeza que deseja limpar todo o carrinho?"):
            self.carrinho_pdv = {}
            self.atualizar_carrinho_pdv_gui()
            self.exibir_mensagem("Carrinho limpo.")

    def finalizar_venda_pdv(self):
        id_cli = self.vendas_cliente_id_combo.get().strip()
        if not id_cli:
            self.exibir_mensagem("Por favor, selecione um Cliente para finalizar a venda.", True)
            return
        
        if not self.carrinho_pdv:
            self.exibir_mensagem("O carrinho está vazio. Adicione itens antes de finalizar a venda.", True)
            return

        if not messagebox.askyesno("Confirmar Venda", f"Deseja finalizar a venda para o cliente {id_cli} com {len(self.carrinho_pdv)} item(s) no carrinho?"):
            return

        # Verificar estoque final antes de criar o pedido
        erros_estoque_prevenda = []
        for id_prod, item_data in self.carrinho_pdv.items():
            produto_obj = item_data["produto"]
            quantidade = item_data["quantidade"]
            if produto_obj.estoque < quantidade:
                erros_estoque_prevenda.append(f"Estoque insuficiente para '{produto_obj.nome}'. Disponível: {produto_obj.estoque}, solicitado: {quantidade}.")
        
        if erros_estoque_prevenda:
            self.exibir_mensagem(f"Venda não pode ser finalizada devido a erros de estoque:\n" + "\n".join(erros_estoque_prevenda), True)
            return

        success_pedido, msg_pedido, novo_pedido = self.lanchonete.criar_pedido(id_cli)
        if not success_pedido:
            self.exibir_mensagem(f"Erro ao criar pedido: {msg_pedido}", True)
            return

        for id_prod, item_data in self.carrinho_pdv.items():
            produto_obj = item_data["produto"]
            quantidade = item_data["quantidade"]
            
            # Adicionar item ao pedido e deduzir estoque
            success_add_item, msg_add_item = novo_pedido.adicionar_item(produto_obj, quantidade)
            if not success_add_item:
                # Isso não deveria ocorrer se a verificação inicial de estoque for bem-sucedida,
                # mas é um fallback de segurança.
                self.exibir_mensagem(f"Erro inesperado ao adicionar item '{produto_obj.nome}' ao pedido: {msg_add_item}. Venda cancelada.", True)
                self.lanchonete.pedidos.pop(novo_pedido.id_pedido) # Remove o pedido criado
                self.lanchonete.salvar_dados()
                return
            
            # A dedução do estoque agora é feita dentro de lanchonete.adicionar_item_a_pedido,
            # ou deve ser feita aqui se o pedido.adicionar_item não deduzir.
            # No seu modelo atual, a dedução do estoque é feita dentro de Lanchonete.adicionar_item_a_pedido
            # e também em Pedido.adicionar_item (onde o estoque é decrementado se for um novo item).
            # Para evitar dupla dedução, o estoque do produto não deve ser decrementado aqui novamente.
            # A lógica mais limpa seria: Pedido.adicionar_item faz a checagem e atualização do estoque,
            # e Lanchonete.adicionar_item_a_pedido apenas chama Pedido.adicionar_item.
            # No seu código atual, `Lanchonete.adicionar_item_a_pedido` faz a dedução,
            # e `Pedido.adicionar_item` também. Vamos corrigir a lógica do modelo para evitar isso.

            # Correção: Removi a dedução duplicada do estoque aqui.
            # O estoque é deduzido quando o status do pedido se torna "Entregue" (seja via UI ou programa)
            # ou quando o item é adicionado a um pedido (que é o que está acontecendo agora).
            # Para o PDV, a dedução deve ocorrer no momento da finalização para garantir a consistência,
            # e o estoque só é atualizado no banco de dados quando o pedido é entregue.
            # Mudei a lógica novamente: A dedução de estoque deve ocorrer APENAS quando o pedido é "Entregue".
            # O carrinho de PDV apenas "reserva" a quantidade.
            # Vamos reverter a dedução de estoque em `Lanchonete.adicionar_item_a_pedido`
            # e garantir que ela ocorra APENAS quando o status do pedido muda para "Entregue".

            # VERIFIQUE A SEÇÃO ABAIXO (MUDANÇAS NO MODELO Lanchonete E Pedido)
            # A dedução de estoque foi movida para o método `atualizar_status_pedido` do Lanchonete,
            # especificamente quando o status muda para "Entregue".
            # No fluxo do PDV, os itens são adicionados ao pedido (que está "Pendente"),
            # mas o estoque real só é baixado quando o pedido é marcado como "Entregue".

        self.lanchonete.salvar_dados()

        self.exibir_mensagem(f"Venda finalizada! Pedido {novo_pedido.id_pedido} criado para o cliente {id_cli}. Estoque será baixado ao 'Entregar' o pedido.", False)
        self.limpar_carrinho_pdv_gui()
        self.atualizar_lista_pedidos(self.filter_status_combo.get())
        self.atualizar_lista_produtos()
        self.atualizar_lista_produtos_pdv()


# --- Execução Principal do Programa ---
if __name__ == "__main__":
    root = tk.Tk()
    root.state('zoomed')
    app = LanchoneteApp(root)
    root.mainloop()