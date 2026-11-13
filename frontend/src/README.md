# Frontend Nivus — limites dos componentes

App.jsx é o ponto de composição e mantém a sessão, estado compartilhado, polling, chamadas HTTP e ações. Componentes em components/ recebem dados e callbacks por props; eles não fazem chamadas HTTP nem mantêm uma segunda sessão.

- DashboardHeader.jsx: identidade da sessão e atualização manual.
- DashboardNavigation.jsx: troca entre painel e gestão de utilizadores.
- LoginPanel.jsx: formulário de autenticação.
- UserManagementPanel.jsx: gestão de contas.
- PasswordChangeModal.jsx: alteração de senha.
- DashboardPanel.jsx: métricas, gráficos, atuador, limiares e logs.

Durante esta extração, preservar a ordem do conteúdo, estilos inline, textos, nomes e eventos. Uma melhoria visual ou mudança de interação deve ser feita em tarefa separada. A API é same-origin; mantenha API_BASE vazio enquanto Nginx continuar servindo painel e API no mesmo host.
