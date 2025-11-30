// src/pages/HistoricoPage.jsx
import React, { useEffect, useState } from 'react';
import { Container, Row, Col, Card, Button, Spinner, Alert, Badge } from 'react-bootstrap';
import { apiGetInternal } from '../services/apiClient';
import { useNavigate } from 'react-router-dom';

export default function HistoricoPage() {
  const [historico, setHistorico] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    async function carregar() {
      try {
        // Agora o apiGetInternal envia o token, então vai funcionar!
        const dados = await apiGetInternal('/historico');
        setHistorico(dados);
      } catch (e) {
        setError('Erro ao carregar histórico. Verifique se está logado.');
      } finally {
        setLoading(false);
      }
    }
    carregar();
  }, []);

  const verDetalhes = (id) => {
    // Navega para a página de detalhes (que vamos criar no Passo 4)
    navigate(`/historico/${id}`);
  };

  if (loading) return <div className="text-center p-5"><Spinner animation="border" /></div>;
  if (error) return <Container className="py-4"><Alert variant="danger">{error}</Alert></Container>;

  return (
    <Container className="py-4">
      <h2 className="mb-4">Meus Simulados</h2>
      
      {historico.length === 0 ? (
        <Alert variant="info">Você ainda não realizou nenhum simulado.</Alert>
      ) : (
        <Row xs={1} md={2} lg={3} className="g-4">
          {historico.map((item) => (
            <Col key={item.id}>
              <Card className="h-100 shadow-sm hover-card">
                <Card.Body>
                  <div className="d-flex justify-content-between mb-2">
                    <Badge bg="primary">{item.vestibular}</Badge>
                    <small className="text-muted">{new Date(item.data_criacao).toLocaleDateString()}</small>
                  </div>
                  <Card.Title>{item.materia}</Card.Title>
                  <Card.Text>
                    Dificuldade: <strong>{item.dificuldade}</strong><br/>
                    Questões: <strong>{item.num_questoes}</strong>
                  </Card.Text>
                </Card.Body>
                <Card.Footer className="bg-white border-top-0">
                  <Button variant="outline-primary" className="w-100" onClick={() => verDetalhes(item.id)}>
                    Ver Questões e Respostas
                  </Button>
                </Card.Footer>
              </Card>
            </Col>
          ))}
        </Row>
      )}
    </Container>
  );
}