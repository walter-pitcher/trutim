"""
Deep Learning Model Architectures for Wake Word Detection & Keyword Spotting.

Implements multiple state-of-the-art architectures:
1. DS-CNN (Depthwise Separable CNN) - lightweight, fast inference
2. Attention-RNN (BiLSTM + Attention) - high accuracy for wake words
3. TC-ResNet (Temporal Convolution ResNet) - streaming-optimized
4. Conformer - combines CNN + Transformer for best accuracy
5. Multi-Head Attention Keyword Spotter - transformer-based

All models are designed for TensorFlow Lite conversion.
"""
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers, Model
from typing import Tuple, Optional, List
from dataclasses import dataclass


@dataclass
class ModelConfig:
    """Shared configuration for all model architectures."""
    input_shape: Tuple[int, int, int] = (98, 80, 1)  # (frames, mel_bins, channels)
    num_keywords: int = 25
    dropout_rate: float = 0.3
    l2_weight: float = 1e-4
    use_batch_norm: bool = True
    activation: str = 'relu'


class DSCNNBuilder:
    """
    Depthwise Separable CNN — inspired by Google's keyword spotting model.

    Architecture:
    - Standard conv -> BN -> ReLU
    - 4x (Depthwise conv -> BN -> ReLU -> Pointwise conv -> BN -> ReLU)
    - Global average pooling -> Dense -> Softmax

    ~80K parameters — optimized for on-device keyword spotting.
    """

    def __init__(self, config: Optional[ModelConfig] = None):
        self.config = config or ModelConfig()

    def build(self) -> Model:
        reg = keras.regularizers.l2(self.config.l2_weight)
        inp = layers.Input(shape=self.config.input_shape, name='audio_input')

        x = layers.Conv2D(
            64, (10, 4), strides=(2, 2), padding='same',
            kernel_regularizer=reg, name='initial_conv'
        )(inp)
        if self.config.use_batch_norm:
            x = layers.BatchNormalization(name='initial_bn')(x)
        x = layers.Activation(self.config.activation)(x)
        x = layers.Dropout(self.config.dropout_rate)(x)

        ds_configs = [
            (64, (3, 3), (1, 1)),
            (64, (3, 3), (1, 1)),
            (128, (3, 3), (2, 2)),
            (128, (3, 3), (1, 1)),
        ]

        for i, (filters, kernel, stride) in enumerate(ds_configs):
            x = layers.DepthwiseConv2D(
                kernel, strides=stride, padding='same',
                depthwise_regularizer=reg, name=f'dw_conv_{i}'
            )(x)
            if self.config.use_batch_norm:
                x = layers.BatchNormalization(name=f'dw_bn_{i}')(x)
            x = layers.Activation(self.config.activation)(x)

            x = layers.Conv2D(
                filters, (1, 1), padding='same',
                kernel_regularizer=reg, name=f'pw_conv_{i}'
            )(x)
            if self.config.use_batch_norm:
                x = layers.BatchNormalization(name=f'pw_bn_{i}')(x)
            x = layers.Activation(self.config.activation)(x)
            x = layers.Dropout(self.config.dropout_rate)(x)

        x = layers.GlobalAveragePooling2D(name='global_pool')(x)
        x = layers.Dense(256, activation=self.config.activation,
                         kernel_regularizer=reg, name='fc1')(x)
        x = layers.Dropout(self.config.dropout_rate)(x)

        output = layers.Dense(
            self.config.num_keywords, activation='softmax', name='predictions'
        )(x)

        model = Model(inputs=inp, outputs=output, name='DS_CNN_KeywordSpotter')
        return model


class AttentionRNNBuilder:
    """
    Bidirectional LSTM with Multi-Head Attention — for wake word detection.

    Architecture:
    - Conv feature frontend (2 conv blocks)
    - Bidirectional LSTM (2 layers)
    - Multi-Head Self-Attention
    - Dense classifier

    ~250K parameters — balanced accuracy and speed.
    """

    def __init__(self, config: Optional[ModelConfig] = None):
        self.config = config or ModelConfig()

    def build(self) -> Model:
        reg = keras.regularizers.l2(self.config.l2_weight)
        inp = layers.Input(shape=self.config.input_shape, name='audio_input')

        x = layers.Conv2D(32, (3, 3), padding='same', kernel_regularizer=reg)(inp)
        x = layers.BatchNormalization()(x)
        x = layers.Activation(self.config.activation)(x)
        x = layers.MaxPooling2D((2, 2))(x)

        x = layers.Conv2D(64, (3, 3), padding='same', kernel_regularizer=reg)(x)
        x = layers.BatchNormalization()(x)
        x = layers.Activation(self.config.activation)(x)
        x = layers.MaxPooling2D((2, 2))(x)

        shape = x.shape
        x = layers.Reshape((shape[1], shape[2] * shape[3]))(x)

        x = layers.Bidirectional(
            layers.LSTM(128, return_sequences=True, dropout=self.config.dropout_rate,
                        kernel_regularizer=reg),
            name='bilstm_1'
        )(x)
        x = layers.Bidirectional(
            layers.LSTM(128, return_sequences=True, dropout=self.config.dropout_rate,
                        kernel_regularizer=reg),
            name='bilstm_2'
        )(x)

        attention = layers.MultiHeadAttention(
            num_heads=4, key_dim=64, dropout=self.config.dropout_rate,
            name='mha'
        )(x, x)
        x = layers.Add()([x, attention])
        x = layers.LayerNormalization()(x)

        x = layers.GlobalAveragePooling1D()(x)
        x = layers.Dense(128, activation=self.config.activation, kernel_regularizer=reg)(x)
        x = layers.Dropout(self.config.dropout_rate)(x)

        output = layers.Dense(
            self.config.num_keywords, activation='softmax', name='predictions'
        )(x)

        model = Model(inputs=inp, outputs=output, name='Attention_RNN_WakeWord')
        return model


class TCResNetBuilder:
    """
    Temporal Convolution ResNet — optimized for streaming keyword spotting.

    Architecture:
    - 1D temporal convolution frontend
    - Residual blocks with dilated convolutions (increasing dilation)
    - Squeeze-and-Excitation blocks for channel attention
    - Global pooling + classifier

    ~150K parameters — excellent for real-time streaming.
    """

    def __init__(self, config: Optional[ModelConfig] = None):
        self.config = config or ModelConfig()

    def build(self) -> Model:
        reg = keras.regularizers.l2(self.config.l2_weight)
        inp = layers.Input(shape=self.config.input_shape, name='audio_input')

        x = layers.Reshape((self.config.input_shape[0],
                            self.config.input_shape[1] * self.config.input_shape[2]))(inp)

        x = layers.Conv1D(64, 3, padding='causal', kernel_regularizer=reg, name='stem_conv')(x)
        x = layers.BatchNormalization()(x)
        x = layers.Activation(self.config.activation)(x)

        channel_configs = [
            (64, 3, 1), (64, 3, 2), (64, 3, 4),
            (128, 3, 1), (128, 3, 2), (128, 3, 4),
        ]

        for i, (filters, kernel_size, dilation) in enumerate(channel_configs):
            x = self._residual_block(x, filters, kernel_size, dilation, reg, f'res_{i}')

        x = self._squeeze_excitation(x, ratio=8, name='se_block')

        x = layers.GlobalAveragePooling1D(name='global_pool')(x)
        x = layers.Dense(128, activation=self.config.activation, kernel_regularizer=reg)(x)
        x = layers.Dropout(self.config.dropout_rate)(x)

        output = layers.Dense(
            self.config.num_keywords, activation='softmax', name='predictions'
        )(x)

        model = Model(inputs=inp, outputs=output, name='TC_ResNet_Streaming')
        return model

    def _residual_block(self, x, filters, kernel_size, dilation, reg, name_prefix):
        """Residual block with dilated causal convolution."""
        residual = x

        y = layers.Conv1D(
            filters, kernel_size, dilation_rate=dilation, padding='causal',
            kernel_regularizer=reg, name=f'{name_prefix}_conv1'
        )(x)
        y = layers.BatchNormalization(name=f'{name_prefix}_bn1')(y)
        y = layers.Activation(self.config.activation)(y)
        y = layers.Dropout(self.config.dropout_rate)(y)

        y = layers.Conv1D(
            filters, kernel_size, dilation_rate=dilation, padding='causal',
            kernel_regularizer=reg, name=f'{name_prefix}_conv2'
        )(y)
        y = layers.BatchNormalization(name=f'{name_prefix}_bn2')(y)

        if residual.shape[-1] != filters:
            residual = layers.Conv1D(
                filters, 1, padding='same', kernel_regularizer=reg,
                name=f'{name_prefix}_skip'
            )(residual)

        y = layers.Add()([residual, y])
        y = layers.Activation(self.config.activation)(y)
        return y

    def _squeeze_excitation(self, x, ratio=8, name='se'):
        """Squeeze-and-Excitation block for channel attention."""
        channels = x.shape[-1]
        se = layers.GlobalAveragePooling1D(name=f'{name}_squeeze')(x)
        se = layers.Dense(channels // ratio, activation='relu', name=f'{name}_fc1')(se)
        se = layers.Dense(channels, activation='sigmoid', name=f'{name}_fc2')(se)
        se = layers.Reshape((1, channels))(se)
        return layers.Multiply(name=f'{name}_scale')([x, se])


class ConformerBuilder:
    """
    Conformer — convolution-augmented Transformer.

    Combines the strengths of CNNs (local feature extraction) and
    Transformers (global dependency modeling) for state-of-the-art
    keyword spotting accuracy.

    Architecture:
    - Subsampling conv frontend
    - N x Conformer blocks (FFN -> MHSA -> Conv -> FFN)
    - Classifier head

    ~500K parameters — highest accuracy, suitable for server-side processing.
    """

    def __init__(self, config: Optional[ModelConfig] = None,
                 num_blocks: int = 4, d_model: int = 144,
                 num_heads: int = 4, conv_kernel_size: int = 15,
                 ff_expansion: int = 4):
        self.config = config or ModelConfig()
        self.num_blocks = num_blocks
        self.d_model = d_model
        self.num_heads = num_heads
        self.conv_kernel_size = conv_kernel_size
        self.ff_expansion = ff_expansion

    def build(self) -> Model:
        inp = layers.Input(shape=self.config.input_shape, name='audio_input')

        x = layers.Reshape((self.config.input_shape[0],
                            self.config.input_shape[1] * self.config.input_shape[2]))(inp)

        x = layers.Dense(self.d_model, name='input_projection')(x)
        x = self._positional_encoding(x)

        for i in range(self.num_blocks):
            x = self._conformer_block(x, name_prefix=f'conformer_{i}')

        x = layers.LayerNormalization(name='final_ln')(x)
        x = layers.GlobalAveragePooling1D(name='global_pool')(x)

        x = layers.Dense(256, activation=self.config.activation, name='fc1')(x)
        x = layers.Dropout(self.config.dropout_rate)(x)

        output = layers.Dense(
            self.config.num_keywords, activation='softmax', name='predictions'
        )(x)

        model = Model(inputs=inp, outputs=output, name='Conformer_KeywordSpotter')
        return model

    def _conformer_block(self, x, name_prefix):
        """
        Conformer block:
        x -> FFN(1/2) -> MHSA -> Conv -> FFN(1/2) -> LayerNorm
        """
        # First feed-forward (half-step)
        ff1 = self._feed_forward(x, name=f'{name_prefix}_ff1')
        x = x + 0.5 * ff1

        # Multi-head self-attention
        attn_out = layers.LayerNormalization(name=f'{name_prefix}_attn_ln')(x)
        attn_out = layers.MultiHeadAttention(
            num_heads=self.num_heads, key_dim=self.d_model // self.num_heads,
            dropout=self.config.dropout_rate, name=f'{name_prefix}_mhsa'
        )(attn_out, attn_out)
        attn_out = layers.Dropout(self.config.dropout_rate)(attn_out)
        x = x + attn_out

        # Convolution module
        conv_out = self._conv_module(x, name=f'{name_prefix}_conv')
        x = x + conv_out

        # Second feed-forward (half-step)
        ff2 = self._feed_forward(x, name=f'{name_prefix}_ff2')
        x = x + 0.5 * ff2

        x = layers.LayerNormalization(name=f'{name_prefix}_ln')(x)
        return x

    def _feed_forward(self, x, name):
        """Feed-forward module with expansion."""
        y = layers.LayerNormalization(name=f'{name}_ln')(x)
        y = layers.Dense(
            self.d_model * self.ff_expansion,
            activation='swish', name=f'{name}_expand'
        )(y)
        y = layers.Dropout(self.config.dropout_rate)(y)
        y = layers.Dense(self.d_model, name=f'{name}_project')(y)
        y = layers.Dropout(self.config.dropout_rate)(y)
        return y

    def _conv_module(self, x, name):
        """
        Conformer convolution module:
        LayerNorm -> Pointwise -> GLU -> Depthwise -> BN -> Swish -> Pointwise -> Dropout
        """
        y = layers.LayerNormalization(name=f'{name}_ln')(x)

        y = layers.Dense(self.d_model * 2, name=f'{name}_pw1')(y)
        y_a, y_b = tf.split(y, 2, axis=-1)
        y = y_a * tf.sigmoid(y_b)  # GLU

        y = layers.Conv1D(
            self.d_model, self.conv_kernel_size, padding='same',
            groups=self.d_model, name=f'{name}_dw'
        )(y)
        y = layers.BatchNormalization(name=f'{name}_bn')(y)
        y = layers.Activation('swish')(y)

        y = layers.Dense(self.d_model, name=f'{name}_pw2')(y)
        y = layers.Dropout(self.config.dropout_rate)(y)
        return y

    def _positional_encoding(self, x):
        """Sinusoidal positional encoding."""
        seq_len = tf.shape(x)[1]
        d_model = self.d_model

        positions = tf.cast(tf.range(seq_len), tf.float32)[:, tf.newaxis]
        dims = tf.cast(tf.range(d_model), tf.float32)[tf.newaxis, :]

        angles = positions / tf.pow(10000.0, 2.0 * (dims // 2) / tf.cast(d_model, tf.float32))

        sin_encoding = tf.sin(angles[:, 0::2])
        cos_encoding = tf.cos(angles[:, 1::2])

        pe = tf.concat([sin_encoding, cos_encoding], axis=-1)
        pe = pe[:, :d_model]
        return x + pe[tf.newaxis, :, :]


class MultiHeadKeywordSpotter:
    """
    Multi-Head Keyword Spotter — dedicated heads for different keyword groups.

    Uses a shared feature backbone with separate classification heads for:
    - Wake word detection (binary: "trutim" / not)
    - Command keywords (call, message, video, etc.)
    - Entity keywords (user names, room names — open vocabulary)

    This architecture enables simultaneous wake word detection and
    command recognition in a single forward pass.
    """

    def __init__(self, config: Optional[ModelConfig] = None,
                 num_command_keywords: int = 15,
                 num_entity_slots: int = 5):
        self.config = config or ModelConfig()
        self.num_command_keywords = num_command_keywords
        self.num_entity_slots = num_entity_slots

    def build(self) -> Model:
        reg = keras.regularizers.l2(self.config.l2_weight)
        inp = layers.Input(shape=self.config.input_shape, name='audio_input')

        # Shared backbone
        x = self._build_backbone(inp, reg)

        # Wake word head (binary)
        wake_word = layers.Dense(64, activation='relu', name='ww_fc')(x)
        wake_word = layers.Dropout(self.config.dropout_rate)(wake_word)
        wake_word_out = layers.Dense(1, activation='sigmoid', name='wake_word')(wake_word)

        # Command keyword head
        command = layers.Dense(128, activation='relu', name='cmd_fc')(x)
        command = layers.Dropout(self.config.dropout_rate)(command)
        command_out = layers.Dense(
            self.num_command_keywords, activation='softmax', name='command'
        )(command)

        # Confidence score head
        confidence = layers.Dense(32, activation='relu', name='conf_fc')(x)
        confidence_out = layers.Dense(1, activation='sigmoid', name='confidence')(confidence)

        model = Model(
            inputs=inp,
            outputs={
                'wake_word': wake_word_out,
                'command': command_out,
                'confidence': confidence_out,
            },
            name='MultiHead_KeywordSpotter'
        )
        return model

    def _build_backbone(self, inp, reg):
        """Shared CNN + BiLSTM feature backbone."""
        x = layers.Conv2D(32, (3, 3), padding='same', kernel_regularizer=reg)(inp)
        x = layers.BatchNormalization()(x)
        x = layers.Activation('relu')(x)
        x = layers.MaxPooling2D((2, 2))(x)

        x = layers.Conv2D(64, (3, 3), padding='same', kernel_regularizer=reg)(x)
        x = layers.BatchNormalization()(x)
        x = layers.Activation('relu')(x)
        x = layers.MaxPooling2D((2, 2))(x)

        x = layers.Conv2D(128, (3, 3), padding='same', kernel_regularizer=reg)(x)
        x = layers.BatchNormalization()(x)
        x = layers.Activation('relu')(x)

        shape = x.shape
        x = layers.Reshape((shape[1], shape[2] * shape[3]))(x)

        x = layers.Bidirectional(
            layers.LSTM(128, return_sequences=True, dropout=0.2, kernel_regularizer=reg)
        )(x)

        x = layers.MultiHeadAttention(
            num_heads=4, key_dim=64, dropout=0.2
        )(x, x)

        x = layers.GlobalAveragePooling1D()(x)
        x = layers.Dense(256, activation='relu', kernel_regularizer=reg)(x)
        x = layers.Dropout(self.config.dropout_rate)(x)
        return x


def build_model(architecture: str = 'ds_cnn',
                config: Optional[ModelConfig] = None) -> Model:
    """
    Factory function to build a keyword spotting model.

    Supported architectures:
    - 'ds_cnn': Depthwise Separable CNN (lightweight)
    - 'attention_rnn': BiLSTM + Attention (balanced)
    - 'tc_resnet': Temporal Convolution ResNet (streaming)
    - 'conformer': Conformer (highest accuracy)
    - 'multi_head': Multi-Head Spotter (simultaneous detection)
    """
    config = config or ModelConfig()

    builders = {
        'ds_cnn': lambda: DSCNNBuilder(config).build(),
        'attention_rnn': lambda: AttentionRNNBuilder(config).build(),
        'tc_resnet': lambda: TCResNetBuilder(config).build(),
        'conformer': lambda: ConformerBuilder(config).build(),
        'multi_head': lambda: MultiHeadKeywordSpotter(config).build(),
    }

    if architecture not in builders:
        raise ValueError(f"Unknown architecture: {architecture}. "
                         f"Choose from: {list(builders.keys())}")

    return builders[architecture]()
