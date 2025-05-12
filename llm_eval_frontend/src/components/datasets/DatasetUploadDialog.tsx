import React, { useState } from 'react';
import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  FormControl,
  FormControlLabel,
  FormLabel,
  Radio,
  RadioGroup,
  Box,
  Typography,
  CircularProgress,
  Alert
} from '@mui/material';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import { DatasetUploadType } from '../../types/dataset';

interface DatasetUploadDialogProps {
  open: boolean;
  onClose: () => void;
  onUpload: (file: File, type: DatasetUploadType) => Promise<void>;
  isUploading: boolean;
}

/**
 * データセットアップロードダイアログ
 */
const DatasetUploadDialog: React.FC<DatasetUploadDialogProps> = ({
  open,
  onClose,
  onUpload,
  isUploading
}) => {
  const [file, setFile] = useState<File | null>(null);
  const [type, setType] = useState<DatasetUploadType>('test');
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0] || null;
    setFile(selectedFile);
    setError(null);

    // ファイル形式のバリデーション
    if (selectedFile && !selectedFile.name.endsWith('.json') && !selectedFile.name.endsWith('.jsonl')) {
      setError('JSONファイル(.json)またはJSONLファイル(.jsonl)のみアップロード可能です。');
    }
  };

  const handleTypeChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setType(event.target.value as DatasetUploadType);
  };

  const handleSubmit = async () => {
    if (!file) {
      setError('ファイルを選択してください。');
      return;
    }

    if (!file.name.endsWith('.json') && !file.name.endsWith('.jsonl')) {
      setError('JSONファイル(.json)またはJSONLファイル(.jsonl)のみアップロード可能です。');
      return;
    }

    try {
      await onUpload(file, type);
      // 成功後にフォームをリセット
      setFile(null);
      setType('test');
      setError(null);
      onClose();
    } catch (err) {
      if (err instanceof Error) {
        setError(`アップロード中にエラーが発生しました: ${err.message}`);
      } else {
        setError('アップロード中に予期しないエラーが発生しました。');
      }
    }
  };

  const handleClose = () => {
    // ダイアログを閉じる際にフォームをリセット
    setFile(null);
    setType('test');
    setError(null);
    onClose();
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>データセットファイルをアップロード</DialogTitle>
      <DialogContent>
        <DialogContentText>
          JSONまたはJSONLファイルを選択して、データセットとしてアップロードしてください。
          ファイル名がデータセット名として使用されます。
        </DialogContentText>

        {error && (
          <Alert severity="error" sx={{ mt: 2, mb: 2 }}>
            {error}
          </Alert>
        )}

        <Box sx={{ mt: 3, mb: 2 }}>
          <FormControl fullWidth>
            <FormLabel id="dataset-type-label">データセットタイプ</FormLabel>
            <RadioGroup
              aria-labelledby="dataset-type-label"
              name="dataset-type"
              value={type}
              onChange={handleTypeChange}
              row
            >
              <FormControlLabel value="test" control={<Radio />} label="テスト用データセット" />
              <FormControlLabel value="n_shot" control={<Radio />} label="n-shot用データセット" />
            </RadioGroup>
          </FormControl>
        </Box>

        <Box
          sx={{
            border: '2px dashed #ccc',
            borderRadius: 2,
            p: 3,
            textAlign: 'center',
            mt: 2
          }}
        >
          <input
            accept=".json,.jsonl"
            id="upload-dataset-file"
            type="file"
            style={{ display: 'none' }}
            onChange={handleFileChange}
          />
          <label htmlFor="upload-dataset-file">
            <Button
              variant="contained"
              component="span"
              startIcon={<CloudUploadIcon />}
              disabled={isUploading}
            >
              ファイルを選択
            </Button>
          </label>

          {file && (
            <Typography variant="body1" sx={{ mt: 2 }}>
              選択したファイル: {file.name}
            </Typography>
          )}
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose} disabled={isUploading}>
          キャンセル
        </Button>
        <Button
          onClick={handleSubmit}
          variant="contained"
          color="primary"
          disabled={!file || isUploading}
        >
          {isUploading ? <CircularProgress size={24} /> : 'アップロード'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default DatasetUploadDialog;
