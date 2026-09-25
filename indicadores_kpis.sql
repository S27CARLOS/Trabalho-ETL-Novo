-- 1. Faturamento Total
SELECT SUM(valor_total) AS faturamento_total 
FROM FatoVendas;

-- 2. Lucro Total
SELECT SUM(lucro) AS lucro_total 
FROM FatoVendas;

-- 3. Volume de Vendas (Quantidade de Itens)
SELECT SUM(quantidade) AS total_itens_vendidos 
FROM FatoVendas;

-- 4. Ticket Médio
SELECT AVG(valor_total) AS ticket_medio 
FROM FatoVendas;

-- 5. Faturamento por Categoria de Produto
SELECT p.categoria, SUM(f.valor_total) AS faturamento_categoria
FROM FatoVendas f
JOIN DimProduto p ON f.id_produto = p.id_produto
GROUP BY p.categoria
ORDER BY faturamento_categoria DESC;

-- 6. Top 5 Clientes por Valor de Compras
SELECT c.nome_cliente, SUM(f.valor_total) AS total_compras
FROM FatoVendas f
JOIN DimCliente c ON f.id_cliente = c.id_cliente
GROUP BY c.nome_cliente
ORDER BY total_compras DESC
LIMIT 5;

-- 7. Evolução Temporal do Faturamento (Mensal e Anual)
SELECT t.ano, t.mes, SUM(f.valor_total) AS faturamento_mensal
FROM FatoVendas f
JOIN DimTempo t ON f.id_tempo = t.id_tempo
GROUP BY t.ano, t.mes
ORDER BY t.ano, t.mes;

-- 8. Desempenho de Vendas por Vendedor
SELECT v.nome_vendedor, SUM(f.valor_total) AS faturamento_vendedor, SUM(f.lucro) AS lucro_vendedor
FROM FatoVendas f
JOIN DimVendedor v ON f.id_vendedor = v.id_vendedor
GROUP BY v.nome_vendedor
ORDER BY faturamento_vendedor DESC;

-- 9. Distribuição Geográfica das Vendas (Por Estado e País)
SELECT r.pais, r.estado, SUM(f.valor_total) AS faturamento_regiao
FROM FatoVendas f
JOIN DimRegiao r ON f.id_regiao = r.id_regiao
GROUP BY r.pais, r.estado
ORDER BY faturamento_regiao DESC;

-- 10. Margem de Lucro Percentual Média
SELECT 
    (SUM(lucro) / NULLIF(SUM(valor_total), 0)) * 100 AS margem_lucro_percentual_media
FROM FatoVendas;
