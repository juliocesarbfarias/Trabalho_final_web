// src/pages/HistoricoDetalhesPage.jsx
import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Container, Card, Spinner, Alert, Badge } from 'react-bootstrap';
import { apiGetInternal } from '../services/apiClient';

export default function HistoricoDetalhesPage() {
  const { id } = useParams();
  const [simulado, setSimulado] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    async function carregarDetalhes() {
      try {
        // Busca o simulado completo com as questões salvas
        const dados = await apiGetInternal(`/simulados/${id}`);
        setSimulado(dados);
      } catch (e) {
        setError('Erro ao carregar detalhes. Tente novamente.');
      } finally {
        setLoading(false);
      }
    }
    carregarDetalhes();
  }, [id]);

  if (loading) return <div className="text-center p-5"><Spinner animation="border" /></div>;
  if (error) return <Container className="py-4"><Alert variant="danger">{error}</Alert></Container>;
  if (!simulado) return null;

  return (
    <Container className="py-4">
      <div className="d-flex align-items-center gap-3 mb-4">
        <Link to="/historico" className="btn btn-outline-secondary">← Voltar</Link>
        <div>
            <h2 className="m-0 text-uppercase">{simulado.vestibular}</h2>
            <span className="text-muted">{simulado.materia} • {simulado.dificuldade}</span>
        </div>
      </div>

      {simulado.questoes.map((q, idx) => (
        <Card key={q.id || idx} className="mb-4 shadow-sm">
          <Card.Header>
            <strong>Questão {idx + 1}</strong>
          </Card.Header>
          <Card.Body>
            <Card.Title className="fs-6 mb-3" style={{ lineHeight: '1.6' }}>
                {q.enunciado}
            </Card.Title>
            
            <div className="d-flex flex-column gap-2">
              {q.opcoes.map((texto, i) => {
                // Verifica se é a resposta correta salva no banco
                const ehCorreta = i === q.resposta_correta_idx;
                
                return (
                  <div 
                    key={i} 
                    className={`p-2 rounded border d-flex align-items-center ${ehCorreta ? 'bg-success bg-opacity-25 border-success' : 'bg-light'}`}
                  >
                    {ehCorreta && <Badge bg="success" className="me-2">Gabarito</Badge>}
                    
                    <span className={ehCorreta ? 'fw-bold text-success' : ''}>
                      {String.fromCharCode(65 + i)}) {texto}
                    </span>
                  </div>
                );
              })}
            </div>
          </Card.Body>
        </Card>
      ))}
    </Container>
  );
}