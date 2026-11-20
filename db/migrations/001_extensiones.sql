-- 001_extensiones.sql
-- Extensiones necesarias. En Supabase se ejecuta tal cual en el SQL Editor;
-- en PostgreSQL 16 plano se requiere la imagen/paquete con pgvector instalado.
create extension if not exists vector;
