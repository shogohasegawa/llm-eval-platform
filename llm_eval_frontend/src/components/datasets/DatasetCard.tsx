import React from 'react';
import { 
  Box, 
  Card, 
  CardContent, 
  Typography, 
  Button, 
  Chip, 
  Stack, 
  IconButton,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import VisibilityIcon from '@mui/icons-material/Visibility';
import { Dataset } from '../../types/dataset';

interface DatasetCardProps {
  dataset: Dataset;
  onDelete: (filePath: string) => void;
  onView: (dataset: Dataset) => void;
}

/**
 * データセット情報を表示するカードコンポーネント
 */
const DatasetCard: React.FC<DatasetCardProps> = ({ dataset, onDelete, onView }) => {
  const [deleteDialogOpen, setDeleteDialogOpen] = React.useState(false);

  // データセットタイプに応じた色を設定
  const getDatasetTypeColor = (type: string) => {
    switch (type) {
      case 'test':
        return '#4CAF50';
      case 'n_shot':
        return '#2196F3';
      default:
        return '#757575';
    }
  };

  const handleDeleteClick = () => {
    setDeleteDialogOpen(true);
  };

  const handleDeleteConfirm = () => {
    onDelete(dataset.file_path || '');
    setDeleteDialogOpen(false);
  };

  const handleDeleteCancel = () => {
    setDeleteDialogOpen(false);
  };

  return (
    <>
      <Card 
        sx={{ 
          mb: 2, 
          height: '100%',
          display: 'flex',
          flexDirection: 'column'
        }}
      >
        <CardContent sx={{ flexGrow: 1 }}>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
            <Typography variant="h6" component="div">
              {dataset.name}
            </Typography>
            <Stack direction="row" spacing={1}>
              <IconButton size="small" onClick={() => onView(dataset)} aria-label="表示">
                <VisibilityIcon fontSize="small" />
              </IconButton>
              <IconButton 
                size="small" 
                onClick={handleDeleteClick} 
                aria-label="削除"
                color="error"
              >
                <DeleteIcon fontSize="small" />
              </IconButton>
            </Stack>
          </Box>
          
          <Box display="flex" alignItems="center" mb={2}>
            <Chip 
              label={dataset.type} 
              size="small" 
              sx={{ 
                backgroundColor: getDatasetTypeColor(dataset.type),
                color: 'white',
                mr: 1
              }} 
            />
            <Typography variant="body2" color="text.secondary">
              {dataset.item_count || dataset.itemCount || dataset.items?.length || 0} アイテム
            </Typography>
          </Box>
          
          {dataset.description && (
            <Typography variant="body2" color="text.secondary" mb={2}>
              {dataset.description}
            </Typography>
          )}
          
          <Box mt={2} display="flex" justifyContent="flex-end">
            <Button 
              variant="outlined" 
              size="small" 
              onClick={() => onView(dataset)}
            >
              詳細を表示
            </Button>
          </Box>
        </CardContent>
      </Card>

      {/* 削除確認ダイアログ */}
      <Dialog
        open={deleteDialogOpen}
        onClose={handleDeleteCancel}
      >
        <DialogTitle>データセットの削除</DialogTitle>
        <DialogContent>
          <DialogContentText>
            データセット「{dataset.name}」を削除してもよろしいですか？
            この操作は元に戻せません。
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleDeleteCancel}>キャンセル</Button>
          <Button onClick={handleDeleteConfirm} color="error" autoFocus>
            削除
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export default DatasetCard;
