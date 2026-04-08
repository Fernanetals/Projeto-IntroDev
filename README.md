# Projeto-IntroDev

Esse projeto é um simulador de uma carteira de investimentos. Atualmente o projeto somente consegue simular compra de ações da bolsa brasileira. É possível criar usuários, buscar por ações da bolsa em tempo real e simular a compra delas. Ao comprar ações elas ficam disponíveis na carteira onde é possível ver alguns dados da ação e o valor total da carteira.

## Tecnologias

O projeto utiliza HTML e CSS com HTMX para o frontend, enquanto o backend utiliza FastAPI e os bancos de dados usaram SQLModel.

## Especificações do Projeto
- O projeto é composto de múltiplas telas que usam HTML, CSS e Javascript, todas configuradas para responsividade entre mobile e pc.
- O framework usado é o FastAPI.
- O CRUD com HTMX é usado, por exemplo, para:
  
  1. Criar usuário com hx-post.
  2. Buscar ação no banco de dados com hx-get.
  3. Atualizar nome de usuário com hx-put.
  4. Deletar usuário com hx-delete.
 
- Foram implementados busca de objetos e paginação do banco de dados de ações.
