-- ========================================
-- CATÁLOGO COMPLETO JORGE CHAVEZ
-- Extraído de las imágenes del catálogo físico
-- ========================================

-- Primero, limpiar la tabla si quieres empezar de cero
-- DELETE FROM catalogo_maestro;

-- ========================================
-- LÍNEA DREAM CURLS (MOOD)
-- ========================================
INSERT INTO catalogo_maestro (nombre, marca, descripcion, costo_estilista, precio_publico) VALUES
('Dream Curls Shampoo 400ml', 'MOOD', 'Shampoo para rizos 400ml', 340.00, 368.00),
('Dream Curls Shampoo 1L', 'MOOD', 'Shampoo para rizos 1 litro', 610.00, 760.00),
('Dream Curls Mask 290ml', 'MOOD', 'Mascarilla para rizos 290ml', 375.00, 490.00),
('Dream Curls Mask 1L', 'MOOD', 'Mascarilla para rizos 1 litro', 575.00, 690.00),
('Dream Curls Leave In 200ml', 'MOOD', 'Leave-in para rizos 200ml', 325.00, 430.00),
('Dream Curls Designer 150ml', 'MOOD', 'Definidor de rizos 150ml', 380.00, 480.00);

-- ========================================
-- LÍNEA DERMA BALANCE (MOOD)
-- ========================================
INSERT INTO catalogo_maestro (nombre, marca, descripcion, costo_estilista, precio_publico) VALUES
('Pre Shampoo 200ml', 'MOOD', 'Pre-tratamiento 200ml', 265.00, 368.00),
('Derma Balance Shampoo 400ml', 'MOOD', 'Shampoo derma balance 400ml', 270.00, 370.00),
('Derma Balance Shampoo 1L', 'MOOD', 'Shampoo derma balance 1 litro', 615.00, 645.00),
('Deep Cleansing Shampoo 1L', 'MOOD', 'Shampoo limpieza profunda 1L', 1155.00, 2029.00);

-- ========================================
-- LÍNEA COLOR PROTECT (MOOD)
-- ========================================
INSERT INTO catalogo_maestro (nombre, marca, descripcion, costo_estilista, precio_publico) VALUES
('Color Protect Shampoo 200ml', 'MOOD', 'Shampoo protector de color 200ml', 225.00, 300.00),
('Color Protect Shampoo 400ml', 'MOOD', 'Shampoo protector de color 400ml', 445.00, 545.00),
('Color Protect Shampoo 1L', 'MOOD', 'Shampoo protector de color 1L', 838.00, 999.00),
('Color Protect Mask', 'MOOD', 'Mascarilla protector de color', 348.00, 438.00);

-- ========================================
-- LÍNEA ULTRA CARE (MOOD)
-- ========================================
INSERT INTO catalogo_maestro (nombre, marca, descripcion, costo_estilista, precio_publico) VALUES
('Ultra Care Shampoo 400ml', 'MOOD', 'Shampoo ultra care 400ml', 320.00, 420.00),
('Ultra Care Shampoo 1L', 'MOOD', 'Shampoo ultra care 1L', 695.00, 860.00),
('Ultra Care Mask 400ml', 'MOOD', 'Mascarilla ultra care 400ml', 420.00, 535.00),
('Ultra Care Mask 1L', 'MOOD', 'Mascarilla ultra care 1L', 695.00, 860.00);

-- ========================================
-- LÍNEA INTENSE REPAIR (MOOD)
-- ========================================
INSERT INTO catalogo_maestro (nombre, marca, descripcion, costo_estilista, precio_publico) VALUES
('Intense Repair Shampoo 400ml', 'MOOD', 'Shampoo reparación intensa 400ml', 320.00, 420.00),
('Intense Repair Shampoo 1L', 'MOOD', 'Shampoo reparación intensa 1L', 695.00, 860.00),
('Intense Repair Mask 400ml', 'MOOD', 'Mascarilla reparación intensa 400ml', 420.00, 535.00),
('Intense Repair Mask 1L', 'MOOD', 'Mascarilla reparación intensa 1L', 695.00, 860.00);

-- ========================================
-- LÍNEA ARGANIKA TREE
-- ========================================
INSERT INTO catalogo_maestro (nombre, marca, descripcion, costo_estilista, precio_publico) VALUES
('Arganika Tree Spray 300ml', 'ARGANIKA', 'Spray protector 300ml', 289.00, 370.00),
('Arganika Tree Shampoo 780ml', 'ARGANIKA', 'Shampoo argán 780ml', 340.00, 480.00);

-- ========================================
-- LÍNEA REIKS - TRATAMIENTOS
-- ========================================
INSERT INTO catalogo_maestro (nombre, marca, descripcion, costo_estilista, precio_publico) VALUES
('Collagen Pro-Color 300ml', 'REIKS', 'Colágeno pro-color 300ml', 200.00, 305.00),
('Keratina Ultra Pro Collagen 1L', 'REIKS', 'Keratina ultra pro 1 litro', 585.00, 750.00),
('Keratina Profesional 1L', 'REIKS', 'Keratina profesional 1 litro', 5400.00, 0.00);

-- ========================================
-- LÍNEA REIKS - SHAMPOOS
-- ========================================
INSERT INTO catalogo_maestro (nombre, marca, descripcion, costo_estilista, precio_publico) VALUES
('Shampoo Minoxidil Biotina 500ml', 'REIKS', 'Shampoo minoxidil 500ml', 205.00, 305.00),
('Shampoo Bergamota Biotina 500ml', 'REIKS', 'Shampoo bergamota 500ml', 205.00, 305.00),
('Shampoo Matiz Negro 300ml', 'REIKS', 'Shampoo matizador negro 300ml', 200.00, 305.00),
('Shampoo Matiz Violeta 300ml', 'REIKS', 'Shampoo matizador violeta 300ml', 200.00, 305.00),
('Shampoo Matiz Azul 300ml', 'REIKS', 'Shampoo matizador azul 300ml', 200.00, 305.00),
('Shampoo Pro-Color 300ml', 'REIKS', 'Shampoo pro-color 300ml', 200.00, 305.00),
('Shampoo Nivelador PH 300ml', 'REIKS', 'Shampoo nivelador pH 300ml', 200.00, 305.00),
('Shampoo Nivelador PH 1L', 'REIKS', 'Shampoo nivelador pH 1L', 585.00, 750.00);

-- ========================================
-- LÍNEA REIKS - MASCARILLAS Y BÁLSAMOS
-- ========================================
INSERT INTO catalogo_maestro (nombre, marca, descripcion, costo_estilista, precio_publico) VALUES
('Mascarilla Violeta 260ml', 'REIKS', 'Mascarilla matizadora violeta', 205.00, 305.00),
('Mascarilla Roja 260ml', 'REIKS', 'Mascarilla matizadora roja', 205.00, 305.00),
('Bálsamo H2O 300ml', 'REIKS', 'Bálsamo activador de rizos', 200.00, 305.00),
('Bálsamo H2O 1L', 'REIKS', 'Bálsamo H2O 1 litro', 585.00, 750.00),
('Mascarilla Chocolate 300ml', 'REIKS', 'Mascarilla de chocolate 300ml', 340.00, 450.00),
('Mascarilla Chocolate 500ml', 'REIKS', 'Mascarilla de chocolate 500ml', 588.00, 725.00),
('Mascarilla Chocolate 1L', 'REIKS', 'Mascarilla de chocolate 1L', 1120.00, 1360.00);

-- ========================================
-- LÍNEA REIKS - TRATAMIENTOS ESPECIALES
-- ========================================
INSERT INTO catalogo_maestro (nombre, marca, descripcion, costo_estilista, precio_publico) VALUES
('Bifásicos 300ml', 'REIKS', 'Tratamiento bifásico 300ml', 275.00, 388.00),
('Kit Ácido Hialurónico', 'REIKS', 'Kit shampoo y mascarilla 480ml', 570.00, 720.00),
('Semi Di Lino 100ml', 'REIKS', 'Semilla de lino 100ml', 265.00, 368.00),
('Suero Nanoreconstructor 300ml', 'REIKS', 'Suero reconstructor 300ml', 340.00, 450.00),
('Suero Nanoreconstructor 1L', 'REIKS', 'Suero reconstructor 1 litro', 1120.00, 1350.00);

-- ========================================
-- VERIFICAR PRODUCTOS INSERTADOS
-- ========================================
-- Para ver cuántos productos se insertaron:
-- SELECT COUNT(*) as total_productos FROM catalogo_maestro;

-- Para ver todos los productos:
-- SELECT * FROM catalogo_maestro ORDER BY marca, nombre;
